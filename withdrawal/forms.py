from django import forms
from .models import EmployeeAccountDetails, WithdrawalCharge

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
        model = WithdrawalCharge
        fields = ["withdrawal_type", "reason", "charge_percentage"]
        widgets = {
            "withdrawal_type": forms.Select(attrs={"class": "form-control"}),
            "reason": forms.Select(attrs={"class": "form-control"}),
            "charge_percentage": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

from .models import WithdrawalRequest


class WithdrawalRequestForm(forms.ModelForm):
    class Meta:
        model = WithdrawalRequest
        fields = ['withdrawal_type', 'reason', 'amount', ]
        widgets = {
            "withdrawal_type": forms.Select(attrs={"class": "form-control"}),
            "reason": forms.Select(attrs={"class": "form-control"}),
            "amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }


    # Dynamic form field for reason
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reason'].required = False

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount

from django import forms
from .models import WithdrawalRequest

class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = WithdrawalRequest
        fields = ['document']  # Only the document field

    def __init__(self, *args, **kwargs):
        """ Dynamically display the required document type based on the reason. """
        self.withdrawal_request = kwargs.pop('withdrawal_request', None)
        super().__init__(*args, **kwargs)

        if self.withdrawal_request:
            document_type = self.withdrawal_request.document_type or "Required Document"
            self.fields['document'].label = f"Upload {document_type}"
            self.fields['document'].widget.attrs.update({'accept': '.pdf', 'class': 'form-control'})  # Only allow PDF uploads


from django import forms
from .models import WithdrawalRequest

class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = WithdrawalRequest
        fields = ['document']  # Only the document field

    def __init__(self, *args, **kwargs):
        """ Dynamically set the document type based on the reason. """
        self.withdrawal_request = kwargs.pop('withdrawal_request', None)
        super().__init__(*args, **kwargs)

        if self.withdrawal_request:
            # Get document type based on reason
            document_type = self.get_document_type(self.withdrawal_request.reason)

            # Assign the document type to the instance and update form label
            self.withdrawal_request.document_type = document_type
            self.fields['document'].label = f"Upload {document_type}"
            self.fields['document'].widget.attrs.update({'accept': '.pdf', 'class': 'form-control'})  # Only allow PDF uploads

    def get_document_type(self, reason):
        """ Returns the required document type based on the reason. """
        document_mapping = {
            'death': 'Death Certificate',
            'voluntary': 'Voluntary Resignation Letter',
            'retirement': 'Retirement Letter',
        }
        return document_mapping.get(reason, "Required Document")


from django import forms
from .models import WithdrawalRequest

class WithdrawalActionForm(forms.ModelForm):
    action_note = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter action note...'}),
        required=True
    )

    class Meta:
        model = WithdrawalRequest
        fields = ['action_note']
        
from django import forms
from .models import WithdrawalTransaction

class WithdrawalTransactionForm(forms.ModelForm):
    """ Form for Admin to process withdrawal transactions manually. """
    paid_full = forms.BooleanField(initial=True, required=False, label="Paid Full")

    class Meta:
        model = WithdrawalTransaction
        fields = ['amount', 'reference_number']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'readonly': True}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
