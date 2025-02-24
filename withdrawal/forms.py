from django import forms
from .models import EmployeeAccountDetails, Charges

class EmployeeAccountForm(forms.ModelForm):
    class Meta:
        model = EmployeeAccountDetails
        fields = ['account_number', 'bank_name', 'account_holder_name']
        widgets = {
            'bank_name': forms.TextInput(attrs={'id': 'bank_name', 'list': 'bankList'}),
            'account_number': forms.TextInput(attrs={'id': 'account_number'}),
        }

    def clean_account_number(self):
        """Ensure the account number contains only digits and is the correct length."""
        account_number = self.cleaned_data['account_number']
        if not account_number.isdigit():
            raise forms.ValidationError("Account number must contain only digits.")
        if len(account_number) < 10:  # Assuming a minimum length of 10 for Nigerian banks
            raise forms.ValidationError("Account number must be at least 10 digits long.")
        return account_number


class WithdrawalChargeForm(forms.ModelForm):
    class Meta:
        model = Charges
        fields = ["charge_percentage"]
        widgets = {
            "charge_percentage": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

from .models import Withdrawals



class WithdrawalActionForm(forms.ModelForm):
    action_note = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter action note...'}),
        required=True
    )

    class Meta:
        model = Withdrawals
        fields = ['action_note']
        
