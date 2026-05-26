from django.db import models
from django.contrib.auth.models import User


class Customer(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='M')
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']


class Policy(models.Model):
    POLICY_TYPES = [
        ('life', 'Life Insurance'),
        ('health', 'Health Insurance'),
        ('vehicle', 'Vehicle Insurance'),
        ('home', 'Home Insurance'),
        ('travel', 'Travel Insurance'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='policies')
    policy_number = models.CharField(max_length=50, unique=True)
    policy_type = models.CharField(max_length=20, choices=POLICY_TYPES)
    cover_amount = models.DecimalField(max_digits=12, decimal_places=2)
    premium_amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.policy_number} — {self.customer.name}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Policies'


class Claim(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('settled', 'Settled'),
    ]

    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='claims')
    claim_number = models.CharField(max_length=50, unique=True)
    claim_date = models.DateField(auto_now_add=True)
    incident_date = models.DateField()
    claim_amount = models.DecimalField(max_digits=12, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    document = models.FileField(upload_to='claims/', null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.claim_number} — {self.policy.customer.name}"

    class Meta:
        ordering = ['-created_at']


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('waived', 'Waived'),
    ]

    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for {self.policy.policy_number} — ₹{self.amount}"

    class Meta:
        ordering = ['due_date']


class PolicyRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    POLICY_TYPES = [
        ('life', 'Life Insurance'),
        ('health', 'Health Insurance'),
        ('vehicle', 'Vehicle Insurance'),
        ('home', 'Home Insurance'),
        ('travel', 'Travel Insurance'),
    ]
    PAYMENT_PLANS = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly (Every 3 months)'),
        ('halfyearly', 'Half Yearly (Every 6 months)'),
        ('yearly', 'Yearly (Once a year)'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='policy_requests')
    policy_type = models.CharField(max_length=20, choices=POLICY_TYPES)
    requested_cover = models.DecimalField(max_digits=12, decimal_places=2)
    payment_plan = models.CharField(max_length=20, choices=PAYMENT_PLANS, default='monthly')
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.name} — {self.get_policy_type_display()} Request"

    class Meta:
        ordering = ['-created_at']