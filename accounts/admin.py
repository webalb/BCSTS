from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from .models import CustomUser

# Custom User Creation Form
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'phone_number', 'nitda_id', 'gender',
                  'passport_photo', 'next_of_kin_name', 'next_of_kin_phone',
                  'next_of_kin_relationship', 'is_active', 'is_staff', 'is_superuser',
                  'groups', 'user_permissions')

# Custom User Change Form
class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = '__all__'

# Custom User Admin
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser

    list_display = ['email', 'first_name', 'last_name', 'nitda_id', 'is_staff']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'gender']
    ordering = ['email']
    search_fields = ['email', 'first_name', 'last_name', 'nitda_id']

    # Remove username from fieldsets
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'other_name', 'phone_number',
                                      'nitda_id', 'gender', 'passport_photo')}),
        ('Next of Kin', {'fields': ('next_of_kin_name', 'next_of_kin_phone', 'next_of_kin_relationship')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Verification', {'fields': ('is_email_verified', 'verification_token')}),
    )

    # Define fields for the Add User form in Django admin
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name',
                       'phone_number', 'nitda_id', 'gender', 'passport_photo',
                       'next_of_kin_name', 'next_of_kin_phone', 'next_of_kin_relationship',
                       'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        """Ensure the correct fieldsets are used when editing users."""
        if obj:
            return self.fieldsets
        return self.add_fieldsets

admin.site.register(CustomUser, CustomUserAdmin)
