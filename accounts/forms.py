from django import forms
from django.contrib.auth.forms import UserCreationForm
from accounts.models import CustomUser
from operations.models import ContributionSetting

# Common class styling function
def apply_form_styling(fields):
    classes = "text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow"
    for field_name, field in fields.items():
        field.widget.attrs['class'] = classes
        if field_name in ['email', 'password1', 'password2']:
            field.widget.attrs['class'] += f' aria-describedby="id_{field_name}_helptext"'

# User Registration Form
class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        help_text="Only NITDA emails (@nitda.gov.ng) are allowed",
        widget=forms.EmailInput(attrs={"placeholder": "example@nitda.gov.ng"}),
    )

    contribution_amount = forms.IntegerField(
        min_value=1000,
        required=True,
        label="Initial Contribution Amount",
        widget=forms.NumberInput(attrs={
            "class": "text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow",
            "placeholder": "Enter contribution amount (min: 1,000)"
        }),
    )

    class Meta:
        model = CustomUser
        fields = [
            "first_name", "last_name", "other_name", "email", "phone_number", "nitda_id", "gender",
            "passport_photo", "next_of_kin_name", "next_of_kin_phone", "next_of_kin_relationship",
            "password1", "password2"
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_form_styling(self.fields)

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email.endswith("@nitda.gov.ng"):
            raise forms.ValidationError("Only NITDA emails (@nitda.gov.ng) are allowed.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

# Employee Creation Form (Admin Use)
class EmployeeForm(UserCreationForm):
    email = forms.EmailField(
        help_text="Only NITDA emails (@nitda.gov.ng) are allowed",
        widget=forms.EmailInput(attrs={"placeholder": "example@nitda.gov.ng"}),
    )
    contribution_amount = forms.IntegerField(
        min_value=1000,
        required=True,
        label="Initial Contribution Amount",
        widget=forms.NumberInput(attrs={
            "class": "text-sm focus:shadow-soft-primary-outline leading-5.6 ease-soft block w-full appearance-none rounded-lg border border-solid border-gray-300 bg-white bg-clip-padding py-2 px-3 font-normal text-gray-700 transition-all focus:border-fuchsia-300 focus:bg-white focus:text-gray-700 focus:outline-none focus:transition-shadow",
            "placeholder": "Enter contribution amount (min: 1,000)"
        }),
    )    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 'nitda_id', 'gender', 'position',
            'passport_photo', "next_of_kin_name", "next_of_kin_phone", "next_of_kin_relationship",
            "password1", "password2"
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_form_styling(self.fields)
    
    def save(self, commit=True):
        employee = super().save(commit=False)
        employee.set_password(self.cleaned_data["password1"])
        if commit:
            employee.save()
        return employee

# Employee Update Form (Admin Use)
class EmployeeUpdateForm(forms.ModelForm):
    email = forms.EmailField(
        help_text="Only NITDA emails (@nitda.gov.ng) are allowed",
        widget=forms.EmailInput(attrs={"placeholder": "example@nitda.gov.ng"}),
    )
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 'nitda_id', 'gender', 'position',
            'passport_photo', "next_of_kin_name", "next_of_kin_phone", "next_of_kin_relationship"
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_form_styling(self.fields)
