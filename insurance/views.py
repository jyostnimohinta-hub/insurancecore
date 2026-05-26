from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Sum, Q
from django.core.mail import send_mail
from django.conf import settings
from datetime import date, timedelta
from .models import Customer, Policy, Claim, Payment
from .forms import LoginForm, CustomerForm, PolicyForm, ClaimForm, ClaimUpdateForm, PaymentForm
from django.contrib.auth.models import User
import uuid
from .models import Customer, Policy, Claim, Payment, PolicyRequest

def landing(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('dashboard')
        else:
            return redirect('customer_portal_dashboard')
    return render(request, 'insurance/landing.html')


# ── Helper: Send Email ────────────────────────────────────────────────────────

def send_notification(subject, message, recipient_email):
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=True,
        )
    except Exception:
        pass


# ── Admin Auth ────────────────────────────────────────────────────────────────

def login_view(request):
    """Admin only login"""
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('dashboard')
        else:
            return redirect('customer_portal_dashboard')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user and user.is_staff:
            login(request, user)
            return redirect('dashboard')
        elif user and not user.is_staff:
            error = 'Please use the Customer Portal to login.'
        else:
            error = 'Invalid admin credentials.'
    return render(request, 'insurance/login.html', {'error': error})

def logout_view(request):
    logout(request)
    return redirect('login')


# ── Admin Dashboard ───────────────────────────────────────────────────────────

def admin_required(view_func):
    """Decorator: only allow staff/admin users"""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_staff:
            return redirect('customer_portal_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

@admin_required
def dashboard(request):
    today = date.today()
    soon = today + timedelta(days=30)
    stats = {
        'customers': Customer.objects.count(),
        'policies': Policy.objects.filter(status='active').count(),
        'claims': Claim.objects.count(),
        'pending_claims': Claim.objects.filter(status='pending').count(),
        'due_payments': Payment.objects.filter(due_date__lte=today + timedelta(days=7), status='pending').count(),
        'expiring_policies': Policy.objects.filter(end_date__lte=soon, status='active').count(),
        'total_cover': Policy.objects.filter(status='active').aggregate(t=Sum('cover_amount'))['t'] or 0,
        'total_premium': Policy.objects.filter(status='active').aggregate(t=Sum('premium_amount'))['t'] or 0,
    }
    recent_claims = Claim.objects.select_related('policy__customer').order_by('-created_at')[:5]
    due_payments = Payment.objects.select_related('policy__customer').filter(
        due_date__lte=today + timedelta(days=7), status='pending'
    ).order_by('due_date')[:5]
    expiring = Policy.objects.select_related('customer').filter(
        end_date__lte=soon, status='active'
    ).order_by('end_date')[:5]
    return render(request, 'insurance/dashboard.html', {
        'stats': stats,
        'recent_claims': recent_claims,
        'due_payments': due_payments,
        'expiring': expiring,
        'today': today,
    })

@admin_required
def chart_data(request):
    today = date.today()
    months = []
    claims_data = []
    payments_data = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12; y -= 1
        months.append(date(y, m, 1).strftime('%b'))
        claims_data.append(Claim.objects.filter(claim_date__year=y, claim_date__month=m).count())
        payments_data.append(
            Payment.objects.filter(due_date__year=y, due_date__month=m, status='paid')
            .aggregate(t=Sum('amount'))['t'] or 0
        )
    policy_dist = list(Policy.objects.values('policy_type').annotate(c=Count('id')).order_by('-c'))
    return JsonResponse({
        'months': months,
        'claims': claims_data,
        'payments': [float(p) for p in payments_data],
        'policy_types': [p['policy_type'] for p in policy_dist],
        'policy_counts': [p['c'] for p in policy_dist],
    })


# ── Customers (Admin) ─────────────────────────────────────────────────────────

@admin_required
def customer_list(request):
    q = request.GET.get('q', '')
    customers = Customer.objects.all()
    if q:
        customers = customers.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q))
    return render(request, 'insurance/customers.html', {'customers': customers, 'q': q})

@admin_required
def customer_add(request):
    form = CustomerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Customer added successfully.')
        return redirect('customers')
    return render(request, 'insurance/customer_form.html', {'form': form, 'title': 'Add Customer'})

@admin_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Customer updated.')
        return redirect('customers')
    return render(request, 'insurance/customer_form.html', {'form': form, 'title': 'Edit Customer', 'obj': customer})

@admin_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    policies = customer.policies.all()
    claims = Claim.objects.filter(policy__customer=customer).order_by('-created_at')
    return render(request, 'insurance/customer_detail.html', {
        'customer': customer, 'policies': policies, 'claims': claims
    })

@admin_required
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == 'POST':
        customer.delete()
        messages.success(request, 'Customer deleted.')
        return redirect('customers')
    return render(request, 'insurance/confirm_delete.html', {'obj': customer, 'type': 'Customer'})


# ── Policies (Admin) ──────────────────────────────────────────────────────────

@admin_required
def policy_list(request):
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    policies = Policy.objects.select_related('customer').all()
    if q:
        policies = policies.filter(Q(policy_number__icontains=q) | Q(customer__name__icontains=q))
    if status:
        policies = policies.filter(status=status)
    return render(request, 'insurance/policies.html', {'policies': policies, 'q': q, 'status': status})

@admin_required
def policy_add(request):
    form = PolicyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        policy = form.save()
        # Send email notification to customer
        if policy.customer.email:
            send_notification(
                subject=f'Policy {policy.policy_number} Created — InsureCore',
                message=f"""Dear {policy.customer.name},

Your insurance policy has been successfully created.

Policy Number : {policy.policy_number}
Policy Type   : {policy.get_policy_type_display()}
Cover Amount  : Rs. {policy.cover_amount}
Premium       : Rs. {policy.premium_amount}
Start Date    : {policy.start_date}
End Date      : {policy.end_date}
Status        : Active

You can login to your customer portal to view full details.

Thank you,
InsureCore Team""",
                recipient_email=policy.customer.email
            )
        messages.success(request, 'Policy created and customer notified.')
        return redirect('policies')
    return render(request, 'insurance/policy_form.html', {'form': form, 'title': 'New Policy'})

@admin_required
def policy_edit(request, pk):
    policy = get_object_or_404(Policy, pk=pk)
    old_status = policy.status
    form = PolicyForm(request.POST or None, instance=policy)
    if request.method == 'POST' and form.is_valid():
        policy = form.save()
        # Notify if status changed to active
        if old_status != 'active' and policy.status == 'active' and policy.customer.email:
            send_notification(
                subject=f'Policy {policy.policy_number} Activated — InsureCore',
                message=f"""Dear {policy.customer.name},

Your policy {policy.policy_number} has been activated.

Cover Amount : Rs. {policy.cover_amount}
Valid Until  : {policy.end_date}

Thank you,
InsureCore Team""",
                recipient_email=policy.customer.email
            )
        messages.success(request, 'Policy updated.')
        return redirect('policies')
    return render(request, 'insurance/policy_form.html', {'form': form, 'title': 'Edit Policy', 'obj': policy})

@admin_required
def policy_detail(request, pk):
    policy = get_object_or_404(Policy, pk=pk)
    claims = policy.claims.all()
    payments = policy.payments.all()
    return render(request, 'insurance/policy_detail.html', {
        'policy': policy, 'claims': claims, 'payments': payments
    })

@admin_required
def policy_delete(request, pk):
    policy = get_object_or_404(Policy, pk=pk)
    if request.method == 'POST':
        policy.delete()
        messages.success(request, 'Policy deleted.')
        return redirect('policies')
    return render(request, 'insurance/confirm_delete.html', {'obj': policy, 'type': 'Policy'})


# ── Claims (Admin) ────────────────────────────────────────────────────────────

@admin_required
def claim_list(request):
    q = request.GET.get('q', '')
    status = request.GET.get('status', '')
    claims = Claim.objects.select_related('policy__customer').all()
    if q:
        claims = claims.filter(Q(claim_number__icontains=q) | Q(policy__customer__name__icontains=q))
    if status:
        claims = claims.filter(status=status)
    return render(request, 'insurance/claims.html', {'claims': claims, 'q': q, 'status': status})

@admin_required
def claim_add(request):
    form = ClaimForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Claim submitted successfully.')
        return redirect('claims')
    return render(request, 'insurance/claim_form.html', {'form': form, 'title': 'Submit Claim'})

@admin_required
def claim_detail(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    old_status = claim.status
    update_form = ClaimUpdateForm(request.POST or None, instance=claim)
    if request.method == 'POST' and update_form.is_valid():
        claim = update_form.save()
        # Send email when claim status changes
        customer_email = claim.policy.customer.email
        customer_name = claim.policy.customer.name
        if old_status != claim.status and customer_email:
            if claim.status == 'approved':
                send_notification(
                    subject=f'Claim {claim.claim_number} Approved — InsureCore',
                    message=f"""Dear {customer_name},

Great news! Your insurance claim has been APPROVED.

Claim Number    : {claim.claim_number}
Claimed Amount  : Rs. {claim.claim_amount}
Approved Amount : Rs. {claim.approved_amount or claim.claim_amount}
Status          : Approved

The settlement will be processed shortly.

Thank you,
InsureCore Team""",
                    recipient_email=customer_email
                )
            elif claim.status == 'rejected':
                send_notification(
                    subject=f'Claim {claim.claim_number} Rejected — InsureCore',
                    message=f"""Dear {customer_name},

We regret to inform you that your claim has been rejected.

Claim Number : {claim.claim_number}
Reason       : {claim.notes or 'Please contact support for details.'}

If you have questions, please contact our support team.

Thank you,
InsureCore Team""",
                    recipient_email=customer_email
                )
            elif claim.status == 'settled':
                send_notification(
                    subject=f'Claim {claim.claim_number} Settled — InsureCore',
                    message=f"""Dear {customer_name},

Your claim has been fully settled.

Claim Number    : {claim.claim_number}
Settled Amount  : Rs. {claim.approved_amount or claim.claim_amount}

Thank you for choosing InsureCore.

InsureCore Team""",
                    recipient_email=customer_email
                )
            elif claim.status == 'under_review':
                send_notification(
                    subject=f'Claim {claim.claim_number} Under Review — InsureCore',
                    message=f"""Dear {customer_name},

Your claim is now under review by our team.

Claim Number : {claim.claim_number}
Status       : Under Review

We will notify you once a decision is made.

Thank you,
InsureCore Team""",
                    recipient_email=customer_email
                )
        messages.success(request, 'Claim updated and customer notified.')
        return redirect('claim_detail', pk=pk)
    return render(request, 'insurance/claim_detail.html', {'claim': claim, 'form': update_form})

@admin_required
def claim_delete(request, pk):
    claim = get_object_or_404(Claim, pk=pk)
    if request.method == 'POST':
        claim.delete()
        messages.success(request, 'Claim deleted.')
        return redirect('claims')
    return render(request, 'insurance/confirm_delete.html', {'obj': claim, 'type': 'Claim'})


# ── Payments (Admin) ──────────────────────────────────────────────────────────

@admin_required
def payment_list(request):
    today = date.today()
    status = request.GET.get('status', '')
    payments = Payment.objects.select_related('policy__customer').all()
    if status:
        payments = payments.filter(status=status)
    return render(request, 'insurance/payments.html', {
        'payments': payments, 'status': status, 'today': today
    })

@admin_required
def payment_add(request):
    form = PaymentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        payment = form.save()
        # Send payment due notification
        customer_email = payment.policy.customer.email
        customer_name = payment.policy.customer.name
        if customer_email:
            send_notification(
                subject=f'Payment Due Reminder — InsureCore',
                message=f"""Dear {customer_name},

This is a reminder that a premium payment is due.

Policy Number : {payment.policy.policy_number}
Amount Due    : Rs. {payment.amount}
Due Date      : {payment.due_date}

Please ensure timely payment to keep your policy active.

Thank you,
InsureCore Team""",
                recipient_email=customer_email
            )
        messages.success(request, 'Payment record added and customer notified.')
        return redirect('payments')
    return render(request, 'insurance/payment_form.html', {'form': form, 'title': 'Add Payment'})

@admin_required
def payment_mark_paid(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    payment.status = 'paid'
    payment.paid_date = date.today()
    payment.save()
    # Notify customer payment received
    customer_email = payment.policy.customer.email
    if customer_email:
        send_notification(
            subject=f'Payment Received — InsureCore',
            message=f"""Dear {payment.policy.customer.name},

Your payment has been received and confirmed.

Policy Number    : {payment.policy.policy_number}
Amount Paid      : Rs. {payment.amount}
Payment Date     : {payment.paid_date}
Status           : Paid

Thank you for your timely payment.

InsureCore Team""",
            recipient_email=customer_email
        )
    messages.success(request, 'Payment marked as paid and customer notified.')
    return redirect('payments')


# ── Send Due Payment Reminders (Admin Action) ─────────────────────────────────

@admin_required
def send_due_reminders(request):
    """Send email reminders to all customers with payments due in 7 days"""
    today = date.today()
    soon = today + timedelta(days=7)
    due_payments = Payment.objects.select_related('policy__customer').filter(
        due_date__lte=soon, due_date__gte=today, status='pending'
    )
    count = 0
    for payment in due_payments:
        customer = payment.policy.customer
        if customer.email:
            send_notification(
                subject=f'Payment Due in {(payment.due_date - today).days} Days — InsureCore',
                message=f"""Dear {customer.name},

URGENT: Your insurance premium payment is due soon.

Policy Number : {payment.policy.policy_number}
Policy Type   : {payment.policy.get_policy_type_display()}
Amount Due    : Rs. {payment.amount}
Due Date      : {payment.due_date}
Days Left     : {(payment.due_date - today).days} days

Please make your payment before the due date to avoid policy lapse.

Thank you,
InsureCore Team""",
                recipient_email=customer.email
            )
            count += 1
    messages.success(request, f'Reminders sent to {count} customers.')
    return redirect('payments')


# ── Customer Portal Auth ──────────────────────────────────────────────────────

def customer_register(request):
    if request.user.is_authenticated and not request.user.is_staff:
        return redirect('customer_portal_dashboard')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        if password1 != password2:
            error = 'Passwords do not match.'
        elif len(password1) < 6:
            error = 'Password must be at least 6 characters.'
        elif User.objects.filter(username=username).exists():
            error = 'Username already taken.'
        elif Customer.objects.filter(email=email).exists():
            error = 'Email already registered.'
        else:
            user = User.objects.create_user(username=username, email=email, password=password1)
            Customer.objects.create(user=user, name=name, email=email, phone=phone)
            login(request, user)
            # Welcome email
            send_notification(
                subject='Welcome to InsureCore Customer Portal',
                message=f"""Dear {name},

Welcome to InsureCore! Your customer portal account has been created successfully.

Username : {username}
Email    : {email}

You can now login to view your policies, submit claims, and track payments.

Portal Link: http://127.0.0.1:8000/portal/login/

Thank you,
InsureCore Team""",
                recipient_email=email
            )
            return redirect('customer_portal_dashboard')
    return render(request, 'insurance/portal/register.html', {'error': error})

def customer_login(request):
    if request.user.is_authenticated and not request.user.is_staff:
        return redirect('customer_portal_dashboard')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user and not user.is_staff:
            login(request, user)
            return redirect('customer_portal_dashboard')
        elif user and user.is_staff:
            error = 'Admins must use the Admin Login page.'
        else:
            error = 'Invalid username or password.'
    return render(request, 'insurance/portal/login.html', {'error': error})

def customer_logout(request):
    logout(request)
    return redirect('customer_login')


# ── Customer Portal Pages ─────────────────────────────────────────────────────

def customer_required(view_func):
    """Decorator: only allow logged-in non-staff customers"""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('customer_login')
        if request.user.is_staff:
            return redirect('dashboard')
        try:
            Customer.objects.get(user=request.user)
        except Customer.DoesNotExist:
            logout(request)
            return redirect('customer_login')
        return view_func(request, *args, **kwargs)
    return wrapper

@customer_required
def customer_portal_dashboard(request):
    customer = Customer.objects.get(user=request.user)
    policies = customer.policies.all()
    claims = Claim.objects.filter(policy__customer=customer).order_by('-created_at')
    payments = Payment.objects.filter(policy__customer=customer, status='pending').order_by('due_date')
    expiring = customer.policies.filter(
        end_date__lte=date.today() + timedelta(days=30), status='active'
    )
    return render(request, 'insurance/portal/dashboard.html', {
        'customer': customer,
        'policies': policies,
        'claims': claims,
        'payments': payments,
        'expiring': expiring,
    })

@customer_required
def customer_portal_policies(request):
    customer = Customer.objects.get(user=request.user)
    policies = customer.policies.all()
    return render(request, 'insurance/portal/policies.html', {
        'customer': customer, 'policies': policies
    })

@customer_required
def customer_portal_claims(request):
    customer = Customer.objects.get(user=request.user)
    # Only show THIS customer's claims
    claims = Claim.objects.filter(policy__customer=customer).order_by('-created_at')
    return render(request, 'insurance/portal/claims.html', {
        'customer': customer, 'claims': claims
    })

@customer_required
def customer_portal_claim_submit(request):
    customer = Customer.objects.get(user=request.user)
    policies = customer.policies.filter(status='active')
    error = None
    success = None
    if request.method == 'POST':
        policy_id = request.POST.get('policy')
        incident_date = request.POST.get('incident_date')
        claim_amount = request.POST.get('claim_amount')
        reason = request.POST.get('reason')
        try:
            # Security: make sure policy belongs to THIS customer
            policy = Policy.objects.get(pk=policy_id, customer=customer)
            claim = Claim.objects.create(
                policy=policy,
                claim_number=f"CLM-{uuid.uuid4().hex[:8].upper()}",
                incident_date=incident_date,
                claim_amount=claim_amount,
                reason=reason,
            )
            if 'document' in request.FILES:
                claim.document = request.FILES['document']
                claim.save()
            # Confirmation email to customer
            send_notification(
                subject=f'Claim {claim.claim_number} Submitted — InsureCore',
                message=f"""Dear {customer.name},

Your claim has been successfully submitted.

Claim Number : {claim.claim_number}
Policy       : {policy.policy_number}
Amount       : Rs. {claim_amount}
Status       : Pending Review

We will notify you once a decision is made.

Thank you,
InsureCore Team""",
                recipient_email=customer.email
            )
            success = f"Claim {claim.claim_number} submitted! A confirmation has been sent to your email."
        except Policy.DoesNotExist:
            error = "Invalid policy selected."
        except Exception as e:
            error = f"Error: {str(e)}"
    return render(request, 'insurance/portal/claim_submit.html', {
        'customer': customer, 'policies': policies,
        'error': error, 'success': success
    })

@customer_required
def customer_portal_payments(request):
    customer = Customer.objects.get(user=request.user)
    # Only show THIS customer's payments
    payments = Payment.objects.filter(policy__customer=customer).order_by('due_date')
    today = date.today()
    return render(request, 'insurance/portal/payments.html', {
        'customer': customer, 'payments': payments, 'today': today
    })

@customer_required
def customer_portal_profile(request):
    customer = Customer.objects.get(user=request.user)
    success = None
    error = None
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        if phone:
            customer.phone = phone
            customer.address = address
            customer.save()
            success = 'Profile updated successfully.'
        else:
            error = 'Phone number is required.'
    return render(request, 'insurance/portal/profile.html', {
        'customer': customer, 'success': success, 'error': error
    })
# Add these views at the bottom of your existing views.py
# (paste after the customer_portal_profile view)

# ── Customer Browse Plans & Request Policy ────────────────────────────────────

@customer_required
def customer_browse_plans(request):
    customer = Customer.objects.get(user=request.user)
    my_requests = PolicyRequest.objects.filter(customer=customer)
    return render(request, 'insurance/portal/plans.html', {
        'customer': customer,
        'my_requests': my_requests,
    })

@customer_required
def customer_request_policy(request):
    customer = Customer.objects.get(user=request.user)
    error = None
    success = None

    # Pre-select type from URL param e.g. ?type=health
    preselect_type = request.GET.get('type', '')

    if request.method == 'POST':
        policy_type = request.POST.get('policy_type')
        requested_cover = request.POST.get('requested_cover')
        payment_plan = request.POST.get('payment_plan')
        message = request.POST.get('message', '')

        if not policy_type or not requested_cover or not payment_plan:
            error = 'Please fill in all required fields.'
        else:
            existing = PolicyRequest.objects.filter(
                customer=customer,
                policy_type=policy_type,
                status='pending'
            ).exists()
            if existing:
                error = 'You already have a pending request for this insurance type. Please wait for it to be reviewed.'
            else:
                try:
                    pr = PolicyRequest.objects.create(
                        customer=customer,
                        policy_type=policy_type,
                        requested_cover=requested_cover,
                        payment_plan=payment_plan,
                        message=message,
                    )
                    type_display = dict(PolicyRequest.POLICY_TYPES).get(policy_type, policy_type)
                    plan_display = dict(PolicyRequest.PAYMENT_PLANS).get(payment_plan, payment_plan)
                    send_notification(
                        subject='Policy Request Received — InsureCore',
                        message=f"""Dear {customer.name},

Your policy request has been received successfully.

Plan Requested : {type_display}
Cover Amount   : Rs. {requested_cover}
Payment Plan   : {plan_display}
Status         : Pending Review

Our team will review your request and activate your policy within 1-2 business days.
You will receive an email once it is approved.

Thank you,
InsureCore Team""",
                        recipient_email=customer.email
                    )
                    success = f"Your request has been submitted! We will notify you at {customer.email} once approved."
                except Exception as e:
                    error = f"Something went wrong: {str(e)}"

    return render(request, 'insurance/portal/request_policy.html', {
        'customer': customer,
        'error': error,
        'success': success,
        'preselect_type': preselect_type,
    })


# ── Admin — Policy Requests ───────────────────────────────────────────────────

@admin_required
def policy_request_list(request):
    requests = PolicyRequest.objects.select_related('customer').all()
    return render(request, 'insurance/policy_requests.html', {'requests': requests})

@admin_required
def policy_request_action(request, pk):
    pr = get_object_or_404(PolicyRequest, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_note = request.POST.get('admin_note', '')
        pr.admin_note = admin_note

        if action == 'approve':
            import uuid as uuid_module

            # Calculate premium based on payment plan
            cover = float(pr.requested_cover)
            yearly_premium = cover * 0.005
            plan = pr.payment_plan
            if plan == 'monthly':
                premium = round(yearly_premium / 12, 2)
            elif plan == 'quarterly':
                premium = round(yearly_premium / 4, 2)
            elif plan == 'halfyearly':
                premium = round(yearly_premium / 2, 2)
            else:
                premium = round(yearly_premium, 2)

            policy = Policy.objects.create(
                customer=pr.customer,
                policy_number=f"POL-{uuid_module.uuid4().hex[:8].upper()}",
                policy_type=pr.policy_type,
                cover_amount=pr.requested_cover,
                premium_amount=premium,
                start_date=date.today(),
                end_date=date.today().replace(year=date.today().year + 1),
                status='active',
            )
            pr.status = 'approved'
            pr.save()

            plan_display = dict(PolicyRequest.PAYMENT_PLANS).get(pr.payment_plan, pr.payment_plan)

            send_notification(
                subject='Policy Approved — InsureCore',
                message=f"""Dear {pr.customer.name},

Great news! Your insurance policy request has been APPROVED.

Policy Number  : {policy.policy_number}
Plan           : {pr.get_policy_type_display()}
Cover Amount   : Rs. {pr.requested_cover}
Premium        : Rs. {policy.premium_amount} {plan_display}
Valid From     : {policy.start_date}
Valid Until    : {policy.end_date}
Status         : Active

Login to your portal to view full details and submit claims.
Portal: http://127.0.0.1:8000/portal/

Thank you for choosing InsureCore.
InsureCore Team""",
                recipient_email=pr.customer.email
            )
            messages.success(request, f'Request approved. Policy {policy.policy_number} created for {pr.customer.name}.')

        elif action == 'reject':
            pr.status = 'rejected'
            pr.save()
            send_notification(
                subject='Policy Request Update — InsureCore',
                message=f"""Dear {pr.customer.name},

We regret to inform you that your policy request could not be approved at this time.

Plan Requested : {pr.get_policy_type_display()}
Status         : Not Approved
Reason         : {admin_note or 'Please contact our support team for more details.'}

You are welcome to submit a new request or contact us for assistance.

Thank you,
InsureCore Team""",
                recipient_email=pr.customer.email
            )
            messages.success(request, f'Request rejected. {pr.customer.name} has been notified.')

    return redirect('policy_request_list')