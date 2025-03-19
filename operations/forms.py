from django import forms
from operations.models import ContributionSetting, TargetSavingsTransaction, Expense, ContributionRecord

class ContributionSettingForm(forms.ModelForm):
    class Meta:
        model = ContributionSetting
        fields = ['amount']
        widgets = {
            'amount': forms.TextInput(),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount < 0:
            raise forms.ValidationError("Contribution amount cannot be negative.")
        return amount
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        classes = "text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow"
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = classes
            

class ContributionSettingAdminForm(forms.ModelForm):
    class Meta:
        model = ContributionSetting
        fields = ['amount']  # 'employee' is excluded from the form fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set 'amount' field to number input with min, step, and initial value
        self.fields['amount'].widget = forms.NumberInput(attrs={
            'min': 1000,
            
        })

        classes = "text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow"
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = classes

class TargetTransactionForm(forms.ModelForm):
    class Meta:
        model = TargetSavingsTransaction
        fields = ['amount', 'receipt']
        widgets = {
            "amount": forms.TextInput(),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount:
            # Remove any commas from the amount string and convert to float
            try:
                amount = float(str(amount).replace(',', ''))
            except (ValueError, TypeError):
                raise forms.ValidationError("Please enter a valid amount.")
            
            # Validate the amount is not negative
            if amount < 0:
                raise forms.ValidationError("Amount cannot be negative.")
                
        return amount
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        classes = "text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow"
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = classes

class TargetWithdrawalPaymentForm(forms.ModelForm):
    class Meta:
        model = TargetSavingsTransaction
        fields = ['receipt']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        classes = "text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow"
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = classes



class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["amount", "description"]
        widgets = {
            "amount": forms.TextInput(),
            "description": forms.Textarea(attrs={"rows": 2, "placeholder": "What this money was used for"}),
        }
    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount:
            # Remove any commas from the amount string and convert to float
            try:
                amount = float(str(amount).replace(',', ''))
            except (ValueError, TypeError):
                raise forms.ValidationError("Please enter a valid amount.")
            
            # Validate the amount is not negative
            if amount < 0:
                raise forms.ValidationError("Amount cannot be negative.")
                
        return amount
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        classes = "text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow"
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = classes
            if field_name == "amount":
                field.widget.attrs['id'] = 'amount'


from datetime import datetime

class ContributionRecordForm(forms.ModelForm):
    MONTH_CHOICES = (
        (1, 'January'),
        (2, 'February'),
        (3, 'March'),
        (4, 'April'),
        (5, 'May'),
        (6, 'June'),
        (7, 'July'),
        (8, 'August'),
        (9, 'September'),
        (10, 'October'),
        (11, 'November'),
        (12, 'December'),
    )

    month = forms.ChoiceField(choices=MONTH_CHOICES, widget=forms.Select(attrs={'class': 'text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow'}))
    year = forms.IntegerField(widget=forms.NumberInput(attrs={'placeholder': 'e.g. 2024', 'class': 'text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow'}))

    class Meta:
        model = ContributionRecord
        fields = ['amount', 'month', 'year']
        widgets = {
            "amount": forms.TextInput(attrs={'class': 'text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow', 'id': 'amount'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount:
            try:
                amount = float(str(amount).replace(',', ''))
            except (ValueError, TypeError):
                raise forms.ValidationError("Please enter a valid amount.")

            if amount < 0:
                raise forms.ValidationError("Amount cannot be negative.")

        return amount

    def clean_year(self):
        year = self.cleaned_data.get("year")
        current_year = datetime.now().year

        if year < 2024: # type: ignore
            raise forms.ValidationError("Year cannot be less than 2024.")

        if year > current_year: # type: ignore
            raise forms.ValidationError(f"Year cannot be greater than the current year ({current_year}).")

        return year



