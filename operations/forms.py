from django import forms
from .models import ContributionSetting, ContributionSettingPermissions

class ContributionSettingForm(forms.ModelForm):
    class Meta:
        model = ContributionSetting
        fields = ['amount']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount < 0:
            raise forms.ValidationError("Contribution amount cannot be negative.")
        return amount


class ContributionSettingAdminForm(forms.ModelForm):
    class Meta:
        model = ContributionSetting
        fields = ['employee', 'amount',]


class ContributionSettingPermissionForm(forms.ModelForm):
    class Meta:
        model = ContributionSettingPermissions
        fields = ['can_update']