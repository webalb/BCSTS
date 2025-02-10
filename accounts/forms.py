from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        help_text="Only NITDA emails (@nitda.gov.ng) are allowed",
        widget=forms.EmailInput(attrs={"placeholder": "example@nitda.gov.ng"}),
    )

    class Meta:
        model = CustomUser
        fields = [
            "first_name", "last_name", "other_name",
            "email", "phone_number", "nitda_id", "gender", 
            "passport_photo", "next_of_kin_name",
            "next_of_kin_phone", "next_of_kin_relationship",
            "password1", "password2",
        ]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email.endswith("@nitda.gov.ng"):
            raise forms.ValidationError("Only NITDA emails (@nitda.gov.ng) are allowed.")
        return email


# for admin to add employee
class EmployeeForm(UserCreationForm):
    email = forms.EmailField(
        help_text="Only NITDA emails (@nitda.gov.ng) are allowed",
        widget=forms.EmailInput(attrs={"placeholder": "example@nitda.gov.ng"}),
    )

    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 
            'nitda_id', 'gender', 'position', 'passport_photo', "next_of_kin_name",
            "next_of_kin_phone", "next_of_kin_relationship",
            "password1", "password2"
        ]

    def __init__(self, *args, **kwargs):
        super(EmployeeForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

# for admin to add employee
class EmployeeUpdateForm(forms.ModelForm):
    email = forms.EmailField(
        help_text="Only NITDA emails (@nitda.gov.ng) are allowed",
        widget=forms.EmailInput(attrs={"placeholder": "example@nitda.gov.ng"}),
    )

    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 
            'nitda_id', 'gender', 'position', 'passport_photo', "next_of_kin_name",
            "next_of_kin_phone", "next_of_kin_relationship"
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'password1' in self.fields:
            del self.fields['password1']
        if 'password2' in self.fields:
            del self.fields['password2']
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
