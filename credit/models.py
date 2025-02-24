import uuid
from decimal import Decimal
from django.db import models
from accounts.models import CustomUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from datetime import datetime


def validate_positive(value):
    if value < Decimal(0):
        raise ValidationError(f"{value} must be a positive number.")


class CreditSettings(models.Model):
    """
    Stores configuration settings for credit applications and policies.
    This model ensures flexibility for administrators to manage credit policies dynamically.
    """

    # Maximum repayment months
    max_repayment_months = models.IntegerField(
        default=10, 
        validators=[MinValueValidator(1), MaxValueValidator(120)],  # Between 1 month and 10 years
        help_text="Maximum number of months allowed for credit repayment."
    )

    # Max savings-to-credit ratio (e.g., 60% for credit, 40% for withdrawal)
    savings_credit_ratio = models.DecimalField(
        max_digits=5, decimal_places=2, 
        default=60.00,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Percentage of savings that can be used for credit (0-100%)."
    )

    # Days when credit applications are open (default: Tuesday & Wednesday)
    OPEN_DAYS_CHOICES = [
        ('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday'), ('Sunday', 'Sunday')
    ]
    open_days = models.JSONField(
        default=['Tuesday', 'Wednesday'],  # ✅ Correct default
        help_text="Days of the week when credit applications are open."
    )


    # Fixed Administrative charge
    admin_charge_value = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=3000.00,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="The fixed amount of administrative charge."
    )

    # Minimum credit amount
    min_credit_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=10000.00,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Minimum amount an applicant can apply for."
    )

    # Credit types enabled
    enable_qard_hasan = models.BooleanField(default=True, help_text="Enable or disable Qard Hasan credit type.")
    enable_murabaha = models.BooleanField(default=True, help_text="Enable or disable Murabaha credit type.")
    enable_musharaka = models.BooleanField(default=True, help_text="Enable or disable Musharaka credit type.")
    enable_ijarah = models.BooleanField(default=True, help_text="Enable or disable Ijarah credit type.")

    # Savings requirement before credit approval
    min_savings_required = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=5000.00,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Minimum savings balance required before being eligible for credit."
    )

    # Metadata
    last_updated = models.DateTimeField(auto_now=True, db_index=True)
    updated_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Last admin who updated the settings."
    )



    def is_application_open_today(self):
        """
        Checks if credit applications are open today.
        """
        from datetime import datetime
        today = datetime.today().strftime("%A")
        return today in self.open_days

 

    def __str__(self):
        return "Credit Settings"

    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # Prevent deletion of the single instance

    @classmethod
    def get_instance(cls):
        return cls.objects.get_or_create(pk=1)[0]  # Always return the single instance

    class Meta:
        verbose_name = "Credit Setting"
        verbose_name_plural = "Credit Settings"

import datetime

class Credit(models.Model):
    CREDIT_TYPE_CHOICES = [
        ('Qard Hasan', 'Qard Hasan (Cash Credit)'),
        ('Murabaha', 'Murabaha (Asset-Based Financing)'),
        ('Musharaka', 'Musharaka (Partnership-Based Financing)'),
        ('Ijarah', 'Ijarah (Leasing-Based Financing)')
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'), ('Approved', 'Approved'),
        ('Rejected', 'Rejected'), ('Cancelled', 'Cancelled'),
        ('Accepted', 'Accepted'), ('Disbursed', 'Disbursed'),
        ('Repaid', 'Repaid')
    ]

    applicant = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="credits")
    credit_type = models.CharField(max_length=50, choices=CREDIT_TYPE_CHOICES)
    amount_requested = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))],
    )
    repayment_period = models.IntegerField(
        validators=[MinValueValidator(1)], help_text="Repayment duration in months."
    )
    date_applied = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    guarantors_approval = models.BooleanField(default=False)
    guarantors_added = models.BooleanField(default=False)

    tracking_id = models.CharField(max_length=10, unique=True, blank=True, null=True)
    administrative_charge = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Fixed administrative charge applied."
    )

    def can_be_cancelled(self):
        """A credit can be canceled only if it is still pending."""
        return self.status == 'Pending'

    def save(self, *args, **kwargs):
        """Ensure credit meets policy settings before saving."""

        # Fetch active credit settings
        settings = CreditSettings.objects.first()
        if not settings:
            raise ValueError("Credit settings are missing. Please configure them first.")

        # Ensure today is an open application day
        today = datetime.datetime.today().strftime('%A')
        if today not in settings.open_days:
            raise ValueError(f"Credit applications are not open on {today}.")

        # Ensure requested amount meets the minimum requirement
        if self.amount_requested < settings.min_credit_amount:
            raise ValueError(f"Minimum credit amount is {settings.min_credit_amount:,}.")

        # Ensure selected credit type is enabled
        if (
            (self.credit_type == 'Qard Hasan' and not settings.enable_qard_hasan) or
            (self.credit_type == 'Murabaha' and not settings.enable_murabaha) or
            (self.credit_type == 'Musharaka' and not settings.enable_musharaka) or
            (self.credit_type == 'Ijarah' and not settings.enable_ijarah)
        ):
            raise ValueError(f"Application for {self.credit_type} is currently disabled.")

        # Assign the default administrative charge from settings
        self.administrative_charge = settings.admin_charge_value

        # Generate unique tracking ID if not set
        if not self.tracking_id:
            self.tracking_id = f"{uuid.uuid4().hex[:6].upper()}{self.credit_type[0]}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.credit_type} - {self.applicant.email} ({self.tracking_id})"

class Guarantor(models.Model):
    guarantor = models.ForeignKey(CustomUser, related_name='guarantors', on_delete=models.CASCADE)
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name='guarantors')
    status_choices = [('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')]
    status = models.CharField(max_length=10, choices=status_choices, default='Pending')
    action_date = models.DateTimeField(null=True, blank=True)
    action_note = models.TextField(blank=True, null=True)

class Murabaha(models.Model):
    credit = models.OneToOneField(Credit, on_delete=models.CASCADE, related_name='murabaha')
    asset_name = models.CharField(max_length=255)
    asset_value = models.DecimalField(max_digits=12, decimal_places=2, validators=[validate_positive])
    profit_margin = models.DecimalField(max_digits=12, decimal_places=2, validators=[validate_positive], blank=True, null=True)
    total_credit_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    vendor_invoice = models.ImageField(upload_to='murabaha/vendor_invoice/', max_length=100, blank=True, null=True)
    created_at = models.DateField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.profit_margin is None:
            self.profit_margin = Decimal(0)
        self.total_credit_amount = (self.asset_value + self.profit_margin)
        super().save(*args, **kwargs)

class QardHasan(models.Model):
    credit = models.OneToOneField(Credit, on_delete=models.CASCADE, related_name='qard_hasan')
    total_credit_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[validate_positive])
    administrative_fee = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[validate_positive])
    created_at = models.DateField(auto_now=True)

class Musharaka(models.Model):
    # include bcs_contribution, ,enhance profit_sharing_ratio such that we could be able to calculate the profit percent of the bcs and the pertner.
    credit = models.OneToOneField(Credit, on_delete=models.CASCADE, related_name='musharaka')
    partner_contribution = models.DecimalField(max_digits=12, decimal_places=2, validators=[validate_positive])
    profit_sharing_ratio = models.DecimalField(max_digits=5, decimal_places=2, validators=[validate_positive])
    created_at = models.DateField(auto_now=True)

class Ijarah(models.Model):
    credit = models.OneToOneField(Credit, on_delete=models.CASCADE, related_name='ijarah')
    asset_name = models.CharField(max_length=255)
    lease_period = models.IntegerField()  # in months
    rental_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[validate_positive])
    created_at = models.DateField(auto_now=True)

class Repayment(models.Model):
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE)
    repayment_date = models.DateTimeField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    remaining_balance = models.DecimalField(max_digits=12, decimal_places=2)
    repayment_method = models.CharField(max_length=1, choices=[('S', 'Salary Deduction'), ('D', 'Direct Deposit')], default='S')
    status = models.CharField(max_length=20, choices=[('Repaid', 'Paid'), ('Pending', 'Pending'), ('Overdue', 'Overdue')])

class TransactionLog(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('R', 'Repayment'),
        ('C', 'Credit Disbursement'),
    ]
    transaction_type = models.CharField(max_length=2, choices=TRANSACTION_TYPE_CHOICES)
    transaction_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_description = models.TextField()
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE)

from django.core.exceptions import ObjectDoesNotExist

class CreditCommittee(models.Model):
    member = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='credit_committee_member')
    role = models.CharField(max_length=50, choices=[('Reviewer', 'Reviewer'), ('Approver', 'Approver')])
    date_added = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        member_email = kwargs.pop('member', None)  # Get email from kwargs, remove it
        is_new = self._state.adding

        if member_email:
            try:
                user = CustomUser.objects.get(email=member_email)
                self.member = user
            except ObjectDoesNotExist:
                # Handle the case where the user with the given email doesn't exist.
                # You might want to raise an exception, create a new user, or log the error.
                raise ValueError(f"User with email {member_email} does not exist.") # or handle how you want.

        super().save(*args, **kwargs)


class CommitteeAction(models.Model):
    committee_member = models.ForeignKey(CreditCommittee, on_delete=models.CASCADE, related_name="actions")
    action_date = models.DateTimeField(auto_now_add=True)
    action_taken = models.CharField(max_length=50, choices=[('Okay', 'Okay'), ('Not Okay', 'Not Okay'), ('Approved', 'Approved'), ('Disapproved', 'Disapproved')])
    action_reason = models.TextField()
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name="committee_actions")
