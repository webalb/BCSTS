import os, re, uuid
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group
from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.utils.crypto import get_random_string
from django.urls import reverse

def validate_nitda_email(value):
    """Ensure the email belongs to the nitda.gov.ng domain."""
    if not re.match(r"^[a-zA-Z0-9._%+-]+@nitda\.gov\.ng$", value):
        raise ValidationError(_("Only @nitda.gov.ng emails are allowed."), code='invalid')

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username field must be set")
        
        extra_fields.setdefault("is_active", True)

        user = self.model(
            username=username,
            email=self.normalize_email(email) if email else None,
            **extra_fields
        )
        
        if password:
            user.set_password(password)
        user.save(using=self._db)

        # Assign default group
        default_group, created = Group.objects.get_or_create(name="Employee")
        user.groups.add(default_group)

        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(username, email, password, **extra_fields)
class CustomUser(AbstractUser):
    id = models.CharField(primary_key=True, max_length=7, unique=True)

    username = models.CharField(
        max_length=50,
        unique=True,
        error_messages={"unique": _("A user with this username already exists.")},
    )

    email = models.EmailField(
        unique=True,
        blank=True,
        null=True,
        error_messages={"unique": _("A user with this email already exists.")},
    )

    full_name = models.CharField(max_length=150, blank=True, null=True)  # Single field for name

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

    nitda_id = models.CharField(max_length=4, unique=True, blank=True, null=True)

    GENDER_CHOICES = [("M", "Male"), ("F", "Female")]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)

    passport_photo = models.ImageField(upload_to="accounts/passports/", blank=True, null=True)

    # Next of Kin
    next_of_kin_name = models.CharField(max_length=100, blank=True, null=True)
    next_of_kin_phone = models.CharField(
        max_length=14,
        blank=True, 
        null=True,
        validators=[
            RegexValidator(
                regex=r"^(\+234|0)[7-9][0-1]\d{8}$",
                message="Enter a valid Nigerian phone number",
            )
        ],
    )
    next_of_kin_relationship = models.CharField(max_length=50)
    position = models.CharField(max_length=100, blank=True, null=True, default='Member')

    is_email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=64, blank=True, null=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['full_name']  # Updated required fields

    objects = CustomUserManager() # type: ignore


    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else self.username

    def get_member_bank_details(self):
        """Retrieve bank details for the user."""
        if self.account_details:  # type: ignore
            return self.account_details  # type: ignore
        return None

    def get_absolute_url(self):
        return reverse('employee_detail', kwargs={'employee_id': self.pk})

    def save(self, *args, **kwargs):
        """Handle passport photo update by deleting the old one when a new one is uploaded."""
        if not self.id:
            while True:
                new_id = uuid.uuid4().hex[:7]
                if not CustomUser.objects.filter(id=new_id).exists():
                    self.id = new_id
                    break

        try:
            existing_user = CustomUser.objects.get(id=self.id)
        except CustomUser.DoesNotExist:
            existing_user = None

        if existing_user and existing_user.passport_photo != self.passport_photo:
            if existing_user.passport_photo:
                old_photo_path = os.path.join(settings.MEDIA_ROOT, str(existing_user.passport_photo))
                if os.path.exists(old_photo_path):
                    os.remove(old_photo_path)

        if not self.verification_token:
            self.verification_token = get_random_string(64)

        super().save(*args, **kwargs)
