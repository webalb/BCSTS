from django import forms
from .models import CreditCommittee, CreditSettings, Credit
from accounts.models import CustomUser
from django.core.exceptions import ObjectDoesNotExist



class CreditApplicationForm(forms.ModelForm):
    class Meta:
        model = Credit
        fields = ['credit_type', 'amount_requested', 'repayment_period']




class CreditCommitteeForm(forms.ModelForm):
    member = forms.CharField(  # Changed to CharField for email input
        label="Member Email",
        widget=forms.TextInput(attrs={
            'class': 'text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow',
            'placeholder': 'Enter member email'  # Added placeholder
        }),
        required=True
    )

    class Meta:
        model = CreditCommittee
        fields = ['member', 'role']
        widgets = {
            'role': forms.Select(attrs={
                'class': 'text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow',
                'required': True
            }),
        }

    def clean_member(self):
        member_email = self.cleaned_data.get('member')
        try:
            user = CustomUser.objects.get(email=member_email)
            return user  # Return the CustomUser object
        except ObjectDoesNotExist:
            raise forms.ValidationError("User with this email does not exist.")

    def save(self, commit=True): # Override save to use the cleaned user object
        member_user = self.cleaned_data['member'] # Get user object from cleaned_data
        instance = super().save(commit=False)
        instance.member = member_user
        if commit:
            instance.save()
        return instance

# Define choices for open_days
DAYS_OF_WEEK = [
    ("Monday", "Monday"),
    ("Tuesday", "Tuesday"),
    ("Wednesday", "Wednesday"),
    ("Thursday", "Thursday"),
    ("Friday", "Friday"),
    ("Saturday", "Saturday"),
    ("Sunday", "Sunday"),
]

class CreditSettingsForm(forms.ModelForm):
    open_days = forms.MultipleChoiceField(
        choices=DAYS_OF_WEEK,
        widget=forms.CheckboxSelectMultiple(attrs={
            "class": "flex flex-wrap gap-3"
        }),
        required=False
    )

    class Meta:
        model = CreditSettings
        fields = [
            "max_repayment_months", "savings_credit_ratio", "open_days",
            "admin_charge_value", "min_credit_amount", "enable_qard_hasan",
            "enable_murabaha", "enable_musharaka", "enable_ijarah",
            "min_savings_required"
        ]
        widgets = {
            "max_repayment_months": forms.NumberInput(attrs={
                "class": "text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow",
                "placeholder": "Enter max repayment months"
            }),
            "savings_credit_ratio": forms.NumberInput(attrs={
                "class": "text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow",
                "placeholder": "Savings-to-Credit Ratio (%)"
            }),
            "admin_charge_value": forms.NumberInput(attrs={
                "class": "text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow",
                "placeholder": "Enter administrative charge"
            }),
            "min_credit_amount": forms.NumberInput(attrs={
                "class": "text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow",
                "placeholder": "Enter minimum credit amount"
            }),
            "enable_qard_hasan": forms.CheckboxInput(attrs={
                "class": "rounded border-gray-300 text-green-600 focus:ring-green-500"
            }),
            "enable_murabaha": forms.CheckboxInput(attrs={
                "class": "rounded border-gray-300 text-green-600 focus:ring-green-500"
            }),
            "enable_musharaka": forms.CheckboxInput(attrs={
                "class": "rounded border-gray-300 text-green-600 focus:ring-green-500"
            }),
            "enable_ijarah": forms.CheckboxInput(attrs={
                "class": "rounded border-gray-300 text-green-600 focus:ring-green-500"
            }),
            "min_savings_required": forms.NumberInput(attrs={
                "class": "text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow",
                "placeholder": "Minimum savings required"
            }),
        }

    def __init__(self, *args, **kwargs):
        """Ensure open_days is properly displayed as a list of selected days."""
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.open_days:
            self.initial["open_days"] = self.instance.open_days

    def clean_open_days(self):
        """Convert list of selected days into a JSON-storable format."""
        return self.cleaned_data["open_days"]
