from accounts.models import CustomUser
from django.db import models
from django.utils.timezone import now
from django.core.mail import send_mail
from django.db.models import Q, Sum
import uuid
from decimal import Decimal
from notification.services import NotificationService
from notification.models   import Notification
from django.urls import reverse

class ContributionSetting(models.Model):
    """ Stores employee's preferred contribution amount and its history. """
    id = models.CharField(primary_key=True, max_length=7, unique=True)

    employee = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="contribution_setting")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee.nitda_id} - Preferred: {self.amount}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding  # Store if it's a new object

        if not self.id:
            while True:
                new_id = uuid.uuid4().hex[:7]
                if not ContributionSetting.objects.filter(id=new_id).exists():
                    self.id = new_id
                    break
        super().save(*args, **kwargs)

        if is_new:  # Now it's safe to create the history entry
            ContributionSettingHistory.objects.create(
                contribution_setting=self,
                amount=self.amount,
                changed_by=self.employee,
                change_reason="Initial setting"
            )
        elif not is_new and self.amount != self._original_amount:
            ContributionSettingHistory.objects.create(
                contribution_setting=self,
                amount=self.amount,
                changed_by=self.employee,
                change_reason="Amount updated"
            )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_amount = self.amount  # Store initial amount for change tracking

class ContributionSettingHistory(models.Model):
    """ Stores the history of contribution setting changes. """
    id = models.CharField(primary_key=True, max_length=7, unique=True)

    contribution_setting = models.ForeignKey(ContributionSetting, on_delete=models.CASCADE, related_name='history')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='contribution_setting_changes')  # Who made the change
    change_reason = models.CharField(max_length=255, blank=True, null=True) # A brief reason explaining the change

    def save(self, *args, **kwargs):
        if not self.id:
            while True:
                new_id = uuid.uuid4().hex[:7]
                if not ContributionSettingHistory.objects.filter(id=new_id).exists():
                    self.id = new_id
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.contribution_setting.employee.nitda_id} - Amount: {self.amount} - Changed at: {self.changed_at}"  

class ContributionChangeRequest(models.Model):
    """ Stores requests from employees to update their contribution amount. """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    id = models.CharField(primary_key=True, max_length=7, unique=True)

    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="contribution_requests")
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_contribution_requests")

    def save(self, *args, **kwargs):
        if not self.id:
            while True:
                new_id = uuid.uuid4().hex[:7]
                if not ContributionChangeRequest.objects.filter(id=new_id).exists():
                    self.id = new_id
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.nitda_id} - Requested: {self.requested_amount} - Status: {self.status}"

class ContributionRecord(models.Model):
    """Logs monthly salary deductions and payment status."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]
    id = models.CharField(primary_key=True, max_length=7, unique=True)
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="contribution_records")
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Deducted amount
    month = models.IntegerField()
    year = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='paid')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'month', 'year')
        ordering = ['-year', '-month']

    def save(self, *args, **kwargs):
        if not self.id:
            while True:
                new_id = uuid.uuid4().hex[:7]
                if not ContributionRecord.objects.filter(id=new_id).exists():
                    self.id = new_id
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.nitda_id} - {self.month}/{self.year}: {self.status}"
    
    @classmethod
    def is_contribution_recorded_for_month(cls, current_month, current_year):
        """Check if the contribution for this month is already recorded."""
        return ContributionRecord.objects.filter(month=current_month, year=current_year).exists()

    @classmethod
    def get_employee_total_contribution(cls, employee):
        """Calculate the total contribution of a specific employee."""
        total = cls.objects.filter(employee=employee, status='paid').aggregate(total=Sum('amount'))['total']
        return total or 0  # Return 0 if no contributions found

    @classmethod
    def get_system_total_contribution(cls):
        """Calculate the total contribution of all employees."""
        total = cls.objects.filter(status='paid').aggregate(total=Sum('amount'))['total']
        return total or 0  # Return 0 if no contributions found

    @classmethod
    def bulk_record_contributions(cls):
        """Create contributions for all employees based on their settings when admin triggers it."""
        current_month = now().month
        current_year = now().year

        # Exclude superusers and users in 'Admin' group
        employees = CustomUser.objects.filter(
            contribution_setting__isnull=False
        ).filter(
            ~Q(is_superuser=True) & ~Q(groups__name="Admin")
        )

        records_created = 0

        for employee in employees:
            contribution_amount = employee.contribution_setting.amount # type: ignore

            # Prevent duplicate entries for the month
            if not cls.objects.filter(employee=employee, month=current_month, year=current_year).exists():
                cls.objects.create(
                    employee=employee,
                    amount=contribution_amount,
                    month=current_month,
                    year=current_year,
                    status='paid' 
                )
                
                # # Send email notification
                # send_mail(
                #     subject="Monthly Contribution Deducted",
                #     message=f"Dear {employee.nitda_id},\n\nYour monthly contribution of {contribution_amount} "
                #             f"has been recorded for {current_month}/{current_year}. Please ensure timely payment.",
                #     from_email="no-reply@bcs.org.ng",
                #     recipient_list=[employee.email],
                #     fail_silently=True
                # )
                message=f"Dear {employee.full_name},\n\nYour monthly contribution of {contribution_amount} has been recorded for {current_month}/{current_year}.",
                NotificationService.send_notification(
                    employee,
                    heading="Monthly Contribution Deducted",
                    message=message,
                    link=reverse("dashboard"),  
                    notification_type=Notification.NotificationType.IN_APP
                )

                records_created += 1

        return records_created  # Return number of created records



class TargetSavings(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('W-R', 'Withdrawal Request'),
        ('completed', 'Completed'),
    ]
    id = models.CharField(primary_key=True, max_length=7, unique=True)
    member = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='target_savings')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    wthdrawed_at = models.DateTimeField(null=True, blank=True)

    def total_savings(self):
        return sum(transaction.amount for transaction in self.transactions.exclude(transaction_type="withdrawal").all()) # type: ignore

    def save(self, *args, **kwargs):
        if not self.id:
            while True:
                new_id = uuid.uuid4().hex[:7]
                if not TargetSavings.objects.filter(id=new_id).exists():
                    self.id = new_id
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.member.full_name} ({self.status})"

class TargetSavingsTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
    ]
    id = models.CharField(primary_key=True, max_length=7, unique=True)
    target_savings = models.ForeignKey(TargetSavings, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPE_CHOICES)
    receipt = models.FileField(upload_to='target_contribution_ransaction/receipts/', blank=True, null=True)
    transaction_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.id:
            while True:
                new_id = uuid.uuid4().hex[:7]
                if not TargetSavingsTransaction.objects.filter(id=new_id).exists():
                    self.id = new_id
                    break
        super().save(*args, **kwargs)



    def __str__(self):
        return f"{self.transaction_type.capitalize()} of ₦{self.amount} on {self.transaction_date}"
