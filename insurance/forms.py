from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Customer, Policy, Claim, Payment
import uuid
from datetime import date


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Username', 'class': 'form-input'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-input'})
    )


class CustomerForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
        required=False
    )

    class Meta:
        model = Customer
        fields = ['name', 'email', 'phone', 'date_of_birth', 'gender', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Full name', 'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email address', 'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'placeholder': '+91 XXXXX XXXXX', 'class': 'form-input'}),
            'gender': forms.Select(attrs={'class': 'form-input'}),
            'address': forms.Textarea(attrs={'placeholder': 'Residential address', 'class': 'form-input', 'rows': 3}),
        }


class PolicyForm(forms.ModelForm):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'})
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'})
    )

    class Meta:
        model = Policy
        fields = ['customer', 'policy_type', 'cover_amount', 'premium_amount', 'start_date', 'end_date', 'description']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-input'}),
            'policy_type': forms.Select(attrs={'class': 'form-input'}),
            'cover_amount': forms.NumberInput(attrs={'placeholder': 'e.g. 10000000', 'class': 'form-input'}),
            'premium_amount': forms.NumberInput(attrs={'placeholder': 'e.g. 5000', 'class': 'form-input'}),
            'description': forms.Textarea(attrs={'placeholder': 'Policy details...', 'class': 'form-input', 'rows': 3}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.policy_number:
            instance.policy_number = f"POL-{uuid.uuid4().hex[:8].upper()}"
        if commit:
            instance.save()
        return instance


class ClaimForm(forms.ModelForm):
    incident_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'})
    )

    class Meta:
        model = Claim
        fields = ['policy', 'incident_date', 'claim_amount', 'reason', 'document']
        widgets = {
            'policy': forms.Select(attrs={'class': 'form-input'}),
            'claim_amount': forms.NumberInput(attrs={'placeholder': 'Claim amount in ₹', 'class': 'form-input'}),
            'reason': forms.Textarea(attrs={'placeholder': 'Describe the incident and reason for claim...', 'class': 'form-input', 'rows': 4}),
            'document': forms.FileInput(attrs={'class': 'form-input'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.claim_number:
            instance.claim_number = f"CLM-{uuid.uuid4().hex[:8].upper()}"
        if commit:
            instance.save()
        return instance


class ClaimUpdateForm(forms.ModelForm):
    class Meta:
        model = Claim
        fields = ['status', 'approved_amount', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-input'}),
            'approved_amount': forms.NumberInput(attrs={'placeholder': 'Approved amount', 'class': 'form-input'}),
            'notes': forms.Textarea(attrs={'placeholder': 'Internal notes...', 'class': 'form-input', 'rows': 3}),
        }


class PaymentForm(forms.ModelForm):
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'})
    )
    paid_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
        required=False
    )

    class Meta:
        model = Payment
        fields = ['policy', 'amount', 'due_date', 'paid_date', 'status', 'transaction_id']
        widgets = {
            'policy': forms.Select(attrs={'class': 'form-input'}),
            'amount': forms.NumberInput(attrs={'placeholder': 'Amount in ₹', 'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-input'}),
            'transaction_id': forms.TextInput(attrs={'placeholder': 'Transaction ID (optional)', 'class': 'form-input'}),
        }