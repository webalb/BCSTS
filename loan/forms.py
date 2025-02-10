from django import forms
from django.db.models import Q
from loan.models import LoanCommittee, Loan, MurabahaLoan, QardHasanLoan, Guarantor
from accounts.models import CustomUser  # Adjust import based on your project structure

class LoanCommitteeForm(forms.ModelForm):
    member = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),  # Set default empty queryset, will be updated in __init__
        label="Select Member"
    )

    class Meta:
        model = LoanCommittee
        fields = ['member', 'role']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'member': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        excluded_users = LoanCommittee.objects.values_list('member_id', flat=True)

        if instance:  # If editing, allow the currently selected user
            self.fields['member'].queryset = CustomUser.objects.filter(
                Q(is_active=True) & ~Q(is_superuser=True) & ~Q(groups__name="admin") &
                (Q(id=instance.member_id) | ~Q(id__in=excluded_users))
            ).distinct()
        else:  # If creating a new entry
            self.fields['member'].queryset = CustomUser.objects.filter(
                Q(is_active=True) & ~Q(is_superuser=True) & ~Q(groups__name="admin") &
                ~Q(id__in=excluded_users)
            ).distinct()




class LoanApplicationForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['loan_type', 'purpose', 'repayment_period']
        widgets = {
            'loan_type': forms.Select(attrs={'class': 'form-control'}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'repayment_period': forms.NumberInput(attrs={'class': 'form-control'}),
        }
from withdrawal.models import EmployeeSavings
from django import forms
from django.core.exceptions import ValidationError

class MurabahaLoanForm(forms.ModelForm):
    class Meta:
        model = MurabahaLoan
        fields = ["asset_name", "asset_value", "asset_image"]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)  # Get and remove request
        super().__init__(*args, **kwargs)

    def clean_asset_value(self):  # Specific field cleaning
        asset_value = self.cleaned_data['asset_value']
        if self.request and self.request.user.is_authenticated: #Check user auth
            try:
                savings = EmployeeSavings.objects.get(employee=self.request.user)
                available_loan = float(savings.total_to_withdraw) * 2
                if asset_value > available_loan:
                    raise ValidationError(f"Asset value should be less than or equal to {available_loan}.")
            except EmployeeSavings.DoesNotExist:
                raise ValidationError("You don't have enough savings to apply for this loan.") #Handle if no savings
        return asset_value


class QardHasanLoanForm(forms.ModelForm):
    class Meta:
        model = QardHasanLoan
        fields = ["total_loan_amount"]

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)  # Get and remove request
        super().__init__(*args, **kwargs)

    def clean_total_loan_amount(self):  # Specific field cleaning
        total_loan_amount = self.cleaned_data['total_loan_amount']
        if self.request and self.request.user.is_authenticated: #Check user auth
            try:
                savings = EmployeeSavings.objects.get(employee=self.request.user)
                available_loan = float(savings.total_to_withdraw) * 2

                if total_loan_amount > available_loan:
                    raise ValidationError(f"Loan amount should be less than or equal to {available_loan}.")
            except EmployeeSavings.DoesNotExist:
                raise ValidationError("You don't have enough savings to apply for this loan.") #Handle if no savings
        return total_loan_amount

class GuarantorForm(forms.Form):
    guarantor_1 = forms.EmailField(required=True, help_text="Enter the email of your first guarantor.")

    def __init__(self, *args, **kwargs):
        loan_type = kwargs.pop('loan_type', None)
        super().__init__(*args, **kwargs)

        if loan_type == 'Murabaha':
            self.fields['guarantor_2'] = forms.EmailField(required=True, help_text="Enter the email of your second guarantor.")

    def clean(self):
        cleaned_data = super().clean()
        guarantor_1 = cleaned_data.get('guarantor_1')
        guarantor_2 = cleaned_data.get('guarantor_2', None)

        if guarantor_1 and guarantor_2 and guarantor_1 == guarantor_2:
            raise forms.ValidationError("Guarantors must have different email addresses.")

        return cleaned_data
from django import forms
from .models import RepaymentSetting
import re

class RepaymentSettingForm(forms.ModelForm):
    class Meta:
        model = RepaymentSetting
        fields = ['repayment_start_date', 'repayment_method']
        
        widgets = {
            'repayment_start_date': forms.DateInput(attrs={'type': 'month', 'class': 'form-control'}),
            'repayment_method': forms.Select(attrs={'class': 'form-control'})
        }

    def clean_repayment_start_date(self):
        repayment_start_date = self.cleaned_data.get('repayment_start_date')

        # Ensure repayment_start_date is in the format YYYY-MM (e.g., 2025-02)
        if repayment_start_date and not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', repayment_start_date):
            raise ValidationError("Invalid format. Use YYYY-MM (e.g., 2025-02).")

        return repayment_start_date

