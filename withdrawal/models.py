from django.db import models
from accounts.models import CustomUser
from django.utils import timezone
from django.db.models import Sum
from operations.models import ContributionRecord  # Assuming this is where contributions are stored
from decimal import Decimal
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError

from django.urls import reverse
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.db import models
import os


class WithdrawalService:
    """Handles validation and processing of withdrawal requests."""

    def __init__(self, withdrawal_request):
        self.withdrawal = withdrawal_request
        self.employee_savings = self.withdrawal.employee.savings
        self.available_balance = self.employee_savings.total_to_withdraw

    def validate_withdrawal(self):
        """Validate withdrawal based on amount, type, and required documents."""
        if self.withdrawal.withdrawal_type == 'partial':
            self._validate_partial_withdrawal()
        elif self.withdrawal.withdrawal_type == 'complete':
            self._validate_complete_withdrawal()
        return True

    def _validate_partial_withdrawal(self):
        """Validation for partial withdrawals (Max 30% rule)."""
        if self.withdrawal.amount > self.employee_savings.available_for_withdrawal():
            raise ValidationError("Partial withdrawal exceeds 30% of total savings.")

    def _validate_complete_withdrawal(self):
        """Validation for complete withdrawals (sufficient balance & documents)."""
        if self.withdrawal.amount > self.available_balance:
            raise ValidationError("Withdrawal amount exceeds available balance.")

        #make sure document is saved

    def move_to_next_stage(self):
        """Move the withdrawal process to the next stage."""
        if self.withdrawal.current_stage < 3:
            self.withdrawal.current_stage += 1
            self.withdrawal.save()
        else:
            raise ValidationError("Withdrawal request process is already completed.")

    def cancel_request(self):
        """Cancel the withdrawal request."""
        self.withdrawal.status = 'cancelled'
        self.withdrawal.save()

class EmployeeSavings(models.Model):
    """ Tracks the total savings of each employee in the cooperative. """
    employee = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="savings")
    total_savings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_to_withdraw(self):
        self.update_savings()
        return self.total_savings
    

    def __str__(self):
        return f"{self.employee.nitda_id} - Savings: {self.total_savings}"

    def calculate_total_contributions(self):
        """ Fetch total contributions from the ContributionRecord model. """
        contributions = ContributionRecord.objects.filter(employee=self.employee)
        return contributions.aggregate(total_contributions=Sum('amount'))['total_contributions'] or 0.00

    def calculate_total_withdrawals(self):
        """ Fetch total withdrawals from the WithdrawalTransaction model. """
        withdrawals = WithdrawalTransaction.objects.filter(request__employee=self.employee)
        return withdrawals.aggregate(total_withdrawals=Sum('amount'))['total_withdrawals'] or 0.00

    def update_savings(self):
        """ Update the employee's total savings based on contributions and withdrawals. """
        total_contributions = self.calculate_total_contributions()
        total_withdrawals = self.calculate_total_withdrawals()
        self.total_savings = float(total_contributions) - float(total_withdrawals)
        self.save()

    def available_for_withdrawal(self):
        """ Returns the available withdrawal amount (30% of total savings). """
        self.update_savings()
        return self.total_savings * 0.30  # 30% withdrawal limit

class WithdrawalCharge(models.Model):
    """ Defines the charges applied on different withdrawal types. """
    withdrawal_type = models.CharField(max_length=50, choices=[('partial', 'Partial'), ('complete', 'Complete')])
    reason = models.CharField(max_length=10, blank=True, null=True, choices=[('death', 'Death'), ('voluntary', 'Voluntary'), ('retirement', 'Retirement')])  # e.g., voluntary withdrawal, death, retirement
    charge_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.withdrawal_type} - {self.reason}: {self.charge_percentage}%"
    
    class Meta:
        unique_together = ('withdrawal_type', 'charge_percentage', 'reason')


class WithdrawalRequest(models.Model):
    """ Manages withdrawal requests for employees with stage tracking and document handling. """

    WITHDRAWAL_TYPES = [
        ('partial', 'Partial'),
        ('complete', 'Complete')
    ]

    REASON_CHOICES = [
        ('death', 'Death'),
        ('voluntary', 'Voluntary'),
        ('retirement', 'Retirement')
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ]

    DOCUMENT_TYPES = {
        'death': 'Death Certificate',
        'voluntary': 'Voluntary Withdrawal Letter',
        'retirement': 'Retirement Letter'
    }

    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="withdrawal_requests")
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    withdrawal_type = models.CharField(max_length=50, choices=WITHDRAWAL_TYPES)
    reason = models.CharField(max_length=10, choices=REASON_CHOICES, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    action_note = models.TextField(blank=True, null=True)
    # Unified Document Storage
    document = models.FileField(upload_to='withdrawals/documents/', blank=True, null=True, 
                                validators=[FileExtensionValidator(allowed_extensions=['pdf'])])
    document_type = models.CharField(max_length=55, blank=True, null=True)  # Stores type based on reason
    is_paid = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    action_on = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Withdrawal Request by {self.employee.nitda_id} - {self.amount}"

    def clean(self):
        """ Validate required fields before saving. """
        if self.withdrawal_type == 'complete' and not self.reason:
            raise ValidationError({"reason": "You must select a reason for complete withdrawal."})

    def save(self, *args, **kwargs):
        """ Automatically update document type based on reason and track application status. """
        if self.reason and not self.document_type:
            self.document_type = self.DOCUMENT_TYPES.get(self.reason)

        # Auto-update status based on document, if set, set status pending, else draft
        
        super().save(*args, **kwargs)


    def cancel_request(self):
        """Cancel the withdrawal request."""
        self.status = 'cancelled'
        self.save()

@receiver(models.signals.post_delete, sender=WithdrawalRequest)
def delete_withdrawal_files(sender, instance, **kwargs):
    """ Remove documents when a withdrawal request is deleted. """
    doc_fields = ['document']
    for field in doc_fields:
        file = getattr(instance, field)
        if file and os.path.isfile(file.path):
            os.remove(file.path)

class WithdrawalTransaction(models.Model):
    """ Logs each withdrawal transaction. """
    request = models.ForeignKey(WithdrawalRequest, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    savings_remain = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    transaction_date = models.DateTimeField(auto_now_add=True)
    reference_number = models.CharField(max_length=255, unique=True, null=True, blank=True)


    def __str__(self):
        return f"{self.request.employee.nitda_id} - {self.amount} - {self.transaction_date}"

    def save(self, *args, **kwargs):
        """ Calculate the charge and final amount after applying the charge. """
        # Get the appropriate charge percentage for this withdrawal type

        try:
            savings = EmployeeSavings.objects.get(employee=self.request.employee)
            savings = savings.total_to_withdraw
            if self.request.withdrawal_type == 'complete':
                withdrawal_charge = WithdrawalCharge.objects.filter(withdrawal_type=self.request.withdrawal_type, reason=self.request.reason).first()
            elif self.request.withdrawal_type == 'partial':
                withdrawal_charge = WithdrawalCharge.objects.filter(withdrawal_type=self.request.withdrawal_type).first()

        except WithdrawalCharge.DoesNotExist:
            withdrawal_charge = None
        
        # Calculate the charge amount
        self.charge = (withdrawal_charge.charge_percentage / 100) * self.amount
        self.final_amount = self.amount + self.charge
        self.savings_remain = float(savings) - float(self.final_amount)
        
        # Save the transaction
        super().save(*args, **kwargs)


class EmployeeAccountDetails(models.Model):
    """ Stores employee bank account details for payments. """
    employee = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="account_details")
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=20)
    account_holder_name = models.CharField(max_length=255)
    
    # Optionally, you could store details about the employee's payment history here.
    # For example, a record of each payment processed could be tracked.
    
    def __str__(self):
        return f"Account Details for {self.employee.nitda_id} - {self.bank_name}"
