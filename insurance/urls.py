from django.urls import path
from . import views

urlpatterns = [
    # ── Home ──────────────────────────────────────────────────────────────────
    path('', views.landing, name='home'),

    # ── Admin Auth ─────────────────────────────────────────────────────────────
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ── Admin Dashboard ────────────────────────────────────────────────────────
    path('dashboard/', views.dashboard, name='dashboard'),
    path('chart-data/', views.chart_data, name='chart_data'),

    # ── Customers (Admin) ──────────────────────────────────────────────────────
    path('customers/', views.customer_list, name='customers'),
    path('customers/add/', views.customer_add, name='customer_add'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),

    # ── Policies (Admin) ───────────────────────────────────────────────────────
    path('policies/', views.policy_list, name='policies'),
    path('policies/add/', views.policy_add, name='policy_add'),
    path('policies/<int:pk>/', views.policy_detail, name='policy_detail'),
    path('policies/<int:pk>/edit/', views.policy_edit, name='policy_edit'),
    path('policies/<int:pk>/delete/', views.policy_delete, name='policy_delete'),

    # ── Claims (Admin) ─────────────────────────────────────────────────────────
    path('claims/', views.claim_list, name='claims'),
    path('claims/add/', views.claim_add, name='claim_add'),
    path('claims/<int:pk>/', views.claim_detail, name='claim_detail'),
    path('claims/<int:pk>/delete/', views.claim_delete, name='claim_delete'),

    # ── Payments (Admin) ───────────────────────────────────────────────────────
    path('payments/', views.payment_list, name='payments'),
    path('payments/add/', views.payment_add, name='payment_add'),
    path('payments/<int:pk>/mark-paid/', views.payment_mark_paid, name='payment_mark_paid'),
    path('payments/send-reminders/', views.send_due_reminders, name='send_due_reminders'),

    # ── Customer Portal ────────────────────────────────────────────────────────
    path('portal/', views.customer_login, name='portal_home'),
    path('portal/register/', views.customer_register, name='customer_register'),
    path('portal/login/', views.customer_login, name='customer_login'),
    path('portal/logout/', views.customer_logout, name='customer_logout'),
    path('portal/dashboard/', views.customer_portal_dashboard, name='customer_portal_dashboard'),
    path('portal/policies/', views.customer_portal_policies, name='customer_portal_policies'),
    path('portal/claims/', views.customer_portal_claims, name='customer_portal_claims'),
    path('portal/claims/submit/', views.customer_portal_claim_submit, name='customer_portal_claim_submit'),
    path('portal/payments/', views.customer_portal_payments, name='customer_portal_payments'),
    path('portal/profile/', views.customer_portal_profile, name='customer_portal_profile'),
# Add these lines inside urlpatterns in insurance/urls.py
# (paste before the closing ] bracket)

    # Customer Plans & Policy Request
    path('portal/plans/', views.customer_browse_plans, name='customer_browse_plans'),
    path('portal/plans/request/', views.customer_request_policy, name='customer_request_policy'),

    # Admin Policy Requests
    path('policy-requests/', views.policy_request_list, name='policy_request_list'),
    path('policy-requests/<int:pk>/action/', views.policy_request_action, name='policy_request_action'),
]