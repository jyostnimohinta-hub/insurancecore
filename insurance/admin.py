from django.contrib import admin
from .models import Customer, Policy, Claim, Payment

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'created_at']
    search_fields = ['name', 'email', 'phone']

@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ['policy_number', 'customer', 'policy_type', 'status', 'end_date']
    list_filter = ['policy_type', 'status']
    search_fields = ['policy_number', 'customer__name']

@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ['claim_number', 'policy', 'claim_amount', 'status', 'claim_date']
    list_filter = ['status']
    search_fields = ['claim_number']

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['policy', 'amount', 'due_date', 'status']
    list_filter = ['status']