from django import forms
from .models import CreditCommittee, CreditSettings, Credit, Murabaha, Musharaka
from accounts.models import CustomUser
from django.core.exceptions import ObjectDoesNotExist


from django import forms
from .models import Credit, Murabaha, Musharaka, Ijarah, Guarantor
from django import forms
from .models import Credit, Murabaha, Musharaka, Ijarah, Guarantor

class CreditApplicationForm(forms.ModelForm):
    class Meta:
        model = Credit
        fields = ['repayment_period']

    # Guarantor email field
    guarantor_email = forms.EmailField(required=True)

    # Credit type-specific fields (optional, will be validated in the view)
    asset_name = forms.CharField(required=False)
    asset_value = forms.DecimalField(required=False)
    vendor_invoice = forms.ImageField(required=False)
    partner_contribution = forms.DecimalField(required=False)
    profit_sharing_ratio = forms.DecimalField(required=False)
    lease_period = forms.IntegerField(required=False)
    rental_amount = forms.DecimalField(required=False)
    amount_requested = forms.DecimalField(required=False)

    def __init__(self, *args, credit_type=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.credit_type = credit_type

    def clean(self):
        cleaned_data = super().clean()
        credit_type = self.credit_type

        # Validate credit type-specific fields
        if credit_type == 'Murabaha':
            if not cleaned_data.get('asset_name') or not cleaned_data.get('vendor_invoice'):
                raise forms.ValidationError("Asset name and vendor invoice are required for Murabaha.")
        elif credit_type == 'Musharaka':
            if not cleaned_data.get('partner_contribution') or not cleaned_data.get('profit_sharing_ratio'):
                raise forms.ValidationError("Partner contribution and profit sharing ratio are required for Musharaka.")
        elif credit_type == 'Ijarah':
            if not cleaned_data.get('lease_period') or not cleaned_data.get('rental_amount'):
                raise forms.ValidationError("Lease period and rental amount are required for Ijarah.")

        return cleaned_data
    
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

