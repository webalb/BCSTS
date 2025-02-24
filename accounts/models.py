import os, re
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.utils.crypto import get_random_string
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

def validate_nitda_email(value):
    """Ensure the email belongs to the nitda.gov.ng domain."""
    if not re.match(r"^[a-zA-Z0-9._%+-]+@nitda\.gov\.ng$", value):
        raise ValidationError(_("Only @nitda.gov.ng emails are allowed."), code='invalid')

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with an email."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)

    
class CustomUser(AbstractUser):
    email = models.EmailField(
        unique=True,
        validators=[validate_nitda_email],
        error_messages={"unique": _("A user with this email already exists.")},
    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    other_name = models.CharField(max_length=50, blank=True, null=True)

    phone_number = models.CharField(
        max_length=14,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^(\+234|0)[7-9][0-1]\d{8}$",
                message="Enter a valid Nigerian phone number",
            )
        ],
    )

    nitda_id = models.CharField(max_length=20, unique=True)

    GENDER_CHOICES = [("M", "Male"), ("F", "Female")]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)

    passport_photo = models.ImageField(upload_to="accounts/passports/", blank=True, null=True)

    # Next of Kin
    next_of_kin_name = models.CharField(max_length=100)
    next_of_kin_phone = models.CharField(
        max_length=14,
        validators=[
            RegexValidator(
                regex=r"^(\+234|0)[7-9][0-1]\d{8}$",
                message="Enter a valid Nigerian phone number",
            )
        ],
    )
    next_of_kin_relationship = models.CharField(max_length=50)
    position = models.CharField(max_length=100, blank=True, null=True, default='Member')  # Default is 'member'


    is_email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=64, blank=True, null=True)
    username = None # this line is important

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = CustomUserManager() # Add this line

    def save(self, *args, **kwargs):
        """Handle passport photo update by deleting the old one when a new one is uploaded."""
        try:
            existing_user = CustomUser.objects.get(id=self.id)
        except CustomUser.DoesNotExist:
            existing_user = None

        if existing_user and existing_user.passport_photo != self.passport_photo:
            # Delete the old passport photo if a new one is uploaded
            if existing_user.passport_photo:
                old_photo_path = os.path.join(settings.MEDIA_ROOT, str(existing_user.passport_photo))
                if os.path.exists(old_photo_path):
                    os.remove(old_photo_path)

        if not self.verification_token:
            self.verification_token = get_random_string(64)

        super().save(*args, **kwargs)
