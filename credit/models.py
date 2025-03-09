import uuid
from decimal import Decimal
from django.db import models
from accounts.models import CustomUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta # type: ignore
import datetime
from django.core.validators import MinValueValidator
from django.core.files.storage import default_storage
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Sum
from django.core.exceptions import ValidationError

from notification.services import NotificationService
from notification.models import Notification

def notify_applicant(credit, heading, body, link):
    """
    Notify Credit Committee members about a new credit request that passed guarantor approval.
    """
    NotificationService.send_notification(
        credit.applicant,
        heading,
        body,
        link,
        notification_type=Notification.NotificationType.IN_APP
    )

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
        default=Decimal(60.00),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        help_text="Percentage of savings that can be used for credit (0-100%)."
    )

    # Days when credit applications are open (default: Tuesday & Wednesday)
    OPEN_DAYS_CHOICES = [
        ('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday'), ('Sunday', 'Sunday')
    ]
    open_days = models.JSONField(
        default=list,  # ✅ Correct default
        help_text="Days of the week when credit applications are open."
    )


    # Fixed Administrative charge
    admin_charge_value = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal(3000.00),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="The fixed amount of administrative charge."
    )

    # Minimum credit amount
    min_credit_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=Decimal(10000.00),
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
        default=Decimal(5000.00),
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
        raise ValidationError("Deletion of CreditSettings instance is not allowed.")

    @classmethod
    def get_instance(cls):
        return cls.objects.get_or_create(pk=1)[0]  # Always return the single instance

    class Meta:
        verbose_name = "Credit Setting"
        verbose_name_plural = "Credit Settings"


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
    id = models.CharField(primary_key=True, max_length=7, unique=True)

    applicant = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="credits")
    credit_type = models.CharField(max_length=50, choices=CREDIT_TYPE_CHOICES)
    amount_requested = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], blank=True, null=True
    )
    repayment_period = models.IntegerField(
        validators=[MinValueValidator(1)], help_text="Repayment duration in months."
    )
    date_applied = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    repayment_start_month = models.CharField(max_length=7, blank=True, null=True, help_text="Date when repayment starts (YYYY-MM).")
    monthly_deduction = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Monthly deduction amount for credit repayment.", blank=True, null=True
    )
    guarantor_approval = models.BooleanField(default=False)

    tracking_id = models.CharField(max_length=10, unique=True, blank=True, null=True)
    administrative_charge = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal(0.00),
        help_text="Fixed administrative charge applied."
    )
    amount_repaid = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    def can_be_cancelled(self):
        """A credit can be canceled only if it is still pending."""
        return self.status == 'Pending'
    

    @property
    def get_credit_type_model(self):
        """
        Returns the specific credit type model instance associated with this credit.
        """
        if self.credit_type == 'Qard Hasan':
            return None
        elif self.credit_type == 'Murabaha':
            return self.murabaha # type: ignore
        elif self.credit_type == 'Musharaka':
            return self.musharaka # type: ignore
        elif self.credit_type == 'Ijarah':
            return self.ijarah # type: ignore
        else:
            raise ValueError(f"Unknown credit type: {self.credit_type}")
    
    @property
    def get_remaining_months(self):
        """Calculate months remaining for repayment."""
        repayment_start_date = self.repayment_start_month_as_date
        if repayment_start_date:
            months_elapsed = (datetime.datetime.now().year - repayment_start_date.year) * 12 + datetime.datetime.now().month - repayment_start_date.month
            if months_elapsed < 0:
                months_elapsed = 0
            return self.repayment_period - months_elapsed
        return self.repayment_period
    
    @property
    def total_repaid(self):
        """Calculate the total amount repaid for this credit."""
        return self.repayment_set.aggregate(total=Sum('amount'))['total'] or Decimal(0) # type: ignore
    
    @property
    def repayment_start_month_as_date(self):
        """Return the repayment start month as a date object (year, month)."""
        if self.repayment_start_month:
            year, month = map(int, self.repayment_start_month.split('-'))
            return datetime.date(year, month, 1)
        return None

    def save(self, *args, **kwargs):
        """Ensure credit meets policy settings before saving."""
        if not self.id:
            while True:
                new_id = uuid.uuid4().hex[:7]
                if not Credit.objects.filter(id=new_id).exists():
                    self.id = new_id
                    break
        
        if self.pk and self.credit_type == 'Murabaha':
            self.amount_requested = self.murabaha.selling_price # type: ignore

        # Fetch active credit settings
        settings = CreditSettings.objects.first()
        if not settings:
            raise ValueError("Credit settings are missing. Please configure them first.")

        # Ensure today is an open application day
        today = datetime.datetime.today().strftime('%A')
        if today not in settings.open_days:
            pass # raise ValueError(f"Credit applications are not open on {today}.")

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
    id = models.CharField(primary_key=True, max_length=7, unique=True)

    guarantor = models.ForeignKey(CustomUser, related_name='guarantors', on_delete=models.CASCADE)
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name='guarantors')
    status_choices = [('Pending', 'Pending'), ('Approved', 'Approved'), ('Declined', 'Declined')]
    status = models.CharField(max_length=10, choices=status_choices, default='Pending')
    action_date = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.id:
            while True:
                new_id = uuid.uuid4().hex[:7]
                if not Guarantor.objects.filter(id=new_id).exists():
                    self.id = new_id
                    break
        super().save(*args, **kwargs)


def validate_file_extension(value):
    valid_extensions = ['.pdf']
    if not any(value.name.lower().endswith(ext) for ext in valid_extensions):
        raise ValidationError(f"Unsupported file extension. Allowed extension is: {', '.join(valid_extensions)}")

class Murabaha(models.Model):

    id = models.CharField(primary_key=True, max_length=7, unique=True)

    credit = models.OneToOneField("Credit", on_delete=models.CASCADE, related_name="murabaha")
    asset_name = models.CharField(max_length=255)
    asset_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[validate_positive])
    profit_margin_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    profit_margin_fixed = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  
    profit_margin = models.DecimalField(max_digits=12, decimal_places=2, validators=[validate_positive], blank=True, null=True)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    vendor_invoice = models.FileField(upload_to="murabaha/vendor_invoice/", max_length=100, blank=True, null=True, validators=[validate_file_extension])
    created_at = models.DateField(auto_now=True)

    def calculate_selling_price(self):
        """
        Calculate and return the selling price.
        """
        if self.profit_margin_fixed is not None:
            return Decimal(self.asset_price) + Decimal(self.profit_margin_fixed)
        elif self.profit_margin_percentage is not None:
            return Decimal(self.asset_price) * (1 + Decimal(self.profit_margin_percentage) / 100)
        return None

    def total_credit_amount(self):
        """
        Calculate the total amount including profit margin.
        """
        return self.selling_price or self.asset_price  # Use selling price if already set

    def save(self, *args, **kwargs):
        # Auto-calculate selling price before saving

        if not self.id:
            while True:
                new_id = uuid.uuid4().hex[:7]
                if not Murabaha.objects.filter(id=new_id).exists():
                    self.id = new_id
                    break
        self.selling_price = self.calculate_selling_price()
        
        if self.selling_price:
            self.profit_margin = Decimal(self.selling_price) - Decimal(self.asset_price)

        if self.pk:
            existing = self.__class__.objects.filter(pk=self.pk).first()
            if existing and existing.vendor_invoice and self.vendor_invoice != existing.vendor_invoice:
                old_invoice_path = existing.vendor_invoice.path
                if default_storage.exists(old_invoice_path):
                    default_storage.delete(old_invoice_path)

        super().save(*args, **kwargs)

class Musharaka(models.Model):
    id = models.CharField(primary_key=True, max_length=7, unique=True)
    credit = models.OneToOneField(Credit, on_delete=models.CASCADE, related_name='musharaka')
    partner_contribution = models.DecimalField(max_digits=12, decimal_places=2, validators=[validate_positive])
    profit_sharing_ratio = models.DecimalField(max_digits=5, decimal_places=2, validators=[validate_positive])
    created_at = models.DateField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.id:
            while True:
                new_id = uuid.uuid4().hex[:7]
                if not Musharaka.objects.filter(id=new_id).exists():
                    self.id = new_id
                    break
        super().save(*args, **kwargs)

class Ijarah(models.Model):
    id = models.CharField(primary_key=True, max_length=7, unique=True)
    credit = models.OneToOneField(Credit, on_delete=models.CASCADE, related_name='ijarah')
    asset_name = models.CharField(max_length=255)
    lease_period = models.IntegerField()  # in months
    rental_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[validate_positive])
    created_at = models.DateField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.id:
            while True:
                new_id = uuid.uuid4().hex[:7]
                if not Ijarah.objects.filter(id=new_id).exists():
                    self.id = new_id
                    break
        super().save(*args, **kwargs)

class Repayment(models.Model):
    id = models.CharField(primary_key=True, max_length=7, unique=True)
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE)
    repayment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    repayment_method = models.CharField(max_length=1, choices=[('S', 'Salary Deduction'), ('D', 'Direct Deposit')], default='S')
    status = models.CharField(max_length=20, choices=[('Repaid', 'Paid'), ('Pending', 'Pending'), ('Overdue', 'Overdue')])

    
    def save(self, *args, **kwargs):
        # Get all existing repayments for this credit
        # Aggregate the amount of existing repayments using SQL
        total_repaid = self.credit.total_repaid
        
        if not self.id:
            while True:
                new_id = uuid.uuid4().hex[:7]
                if not Repayment.objects.filter(id=new_id).exists():
                    self.id = new_id
                    break
        # Add the current amount to the total repaid
        total_repaid += self.amount
        
        
        # Update status based on remaining balance
        if self.credit.amount_requested is not None and total_repaid >= (self.credit.amount_requested - Decimal('1.00')):
            self.status = 'Repaid'
            self.credit.status = 'Repaid'
            self.credit.save()
            heading = "Credit Repayment Completion Notification"
            body = f"Dear {self.credit.applicant.get_full_name()}, congratulations! You have completed the repayment of your credit."
            # link = reverse('credit:transactions')
            link=''
            notify_applicant(self.credit, heading, body, link)
        else:
            self.status = 'Pending'
        
        super().save(*args, **kwargs)

class TransactionLog(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('R', 'Repayment'),
        ('C', 'Credit Disbursement'),
    ]
    id = models.CharField(primary_key=True, max_length=7, unique=True)
    transaction_type = models.CharField(max_length=2, choices=TRANSACTION_TYPE_CHOICES)
    transaction_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_receipt = models.FileField(upload_to='transaction_receipts/', max_length=255, blank=True, null=True)
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if not self.id:
            while True:
                new_id = uuid.uuid4().hex[:7]
                if not TransactionLog.objects.filter(id=new_id).exists():
                    self.id = new_id
                    break
        
        if self.transaction_type == 'R':
            credit = self.credit
            if credit.repayment_start_month and credit.repayment_period:
                year, month = map(int, credit.repayment_start_month.split('-'))
                repayment_end_date = datetime.date(year, month, 1) + relativedelta(months=credit.repayment_period)
                if credit.credit_type == 'Murabaha':
                    total_requested = credit.murabaha.selling_price # type: ignore
                else:
                    total_requested = credit.amount_requested or Decimal(0)
                total_paid = credit.total_repaid
                total_paid += self.amount
                remaining_balance = total_requested - total_paid
                remaining_months = (repayment_end_date.year - datetime.date.today().year) * 12 + (repayment_end_date.month - datetime.date.today().month)
                if remaining_months > 0:
                    credit.monthly_deduction = remaining_balance / remaining_months
                else:
                    credit.monthly_deduction = remaining_balance
                credit.save()
        elif self.transaction_type == 'R-S':
            self.transaction_type = 'R'

        if self.pk:
            existing = self.__class__.objects.filter(pk=self.pk).first()
            if existing and existing.transaction_receipt and self.transaction_receipt != existing.transaction_receipt:
                old_receipt_path = existing.transaction_receipt.path
                if default_storage.exists(old_receipt_path):
                    default_storage.delete(old_receipt_path)

        super().save(*args, **kwargs)


class CreditCommittee(models.Model):

    id = models.CharField(primary_key=True, max_length=7, unique=True)
    member = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='credit_committee_member')
    role = models.CharField(max_length=50, choices=[('Reviewer', 'Reviewer'), ('Approver', 'Approver')])
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.email} - {self.role}"

    def save(self, *args, **kwargs):
        member_email = kwargs.pop('member', None)  # Get email from kwargs, remove it
        is_new = self._state.adding
        if not self.id:
            while True:
                new_id = uuid.uuid4().hex[:7]
                if not CreditCommittee.objects.filter(id=new_id).exists():
                    self.id = new_id
                    break

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
    id = models.CharField(primary_key=True, max_length=7, unique=True)
    committee_member = models.ForeignKey(CreditCommittee, on_delete=models.CASCADE, related_name="actions")
    action_date = models.DateTimeField(auto_now_add=True)
    action_taken = models.CharField(max_length=50, choices=[('Okay', 'Okay'), ('Not Okay', 'Not Okay'), ('Approved', 'Approved'), ('Declined', 'Declined')])
    action_reason = models.TextField()
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name="committee_actions")

    def save(self, *args, **kwargs):
        if not self.id:
            while True:
                new_id = uuid.uuid4().hex[:7]
                if not CommitteeAction.objects.filter(id=new_id).exists():
                    self.id = new_id
                    break
        super().save(*args, **kwargs)