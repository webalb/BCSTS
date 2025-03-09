from django import forms
from operations.models import ContributionSetting, TargetSavingsTransaction

class ContributionSettingForm(forms.ModelForm):
    class Meta:
        model = ContributionSetting
        fields = ['amount']
        widgets = {
            'amount': forms.NumberInput(attrs={'min': '0'}),
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
        fields = ['amount', 'receipt']  # 'employee' is excluded from the form fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['amount'].widget = forms.NumberInput()

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

