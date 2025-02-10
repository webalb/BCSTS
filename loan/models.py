import uuid
from decimal import Decimal
from django.db import models
from accounts.models import CustomUser
from django.core.exceptions import ValidationError
from datetime import datetime

def validate_positive(value):
    if value < Decimal(0):
        raise ValidationError(f"{value} must be a positive number.")

class ActionNote(models.Model):
    ACTION_CHOICES = [
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Cancelled', 'Cancelled'),
        ('Disbursed', 'Disbursed'),
        ('Paid', 'Paid'),
        ('Accepted', 'Accepted')
    ]

    loan = models.ForeignKey('Loan', related_name='action_notes', on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    note = models.TextField()
    action_date = models.DateTimeField(auto_now_add=True)
    action_by = models.ForeignKey(CustomUser, related_name='action_by', on_delete=models.CASCADE)

    def __str__(self):
        return f"Action: {self.action} for Loan ID: {self.loan.id} by {self.action_by.first_name} {self.action_by.last_name}"

class Loan(models.Model):
    LOAN_TYPE_CHOICES = [
        ('Qard Hasan', 'Qard Hasan (Cash Loan)'),
        ('Murabaha', 'Murabaha (Asset-Based Financing)')
    ]
    
    applicant = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    loan_type = models.CharField(max_length=50, choices=LOAN_TYPE_CHOICES)
    purpose = models.TextField()
    repayment_period = models.IntegerField()  # in months
    date_applied = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('Pending', 'Pending'), ('Approved', 'Approved'), 
        ('Rejected', 'Rejected'), ('Cancelled', 'Cancelled'),
        ('Accepted', 'Accepted'), ('Disbursed', 'Disbursed'),
        ('Paid', 'Paid'), ('Not Finished', 'Apllication Not Finish')], default='Not Finished')
    guarantors_approval = models.BooleanField(default=False)
    tracking_id = models.CharField(max_length=7, unique=True, blank=True, null=True)
    repayment_setting = models.BooleanField(default=False)
    guarantors_added = models.BooleanField(default=False)
    details_completed = models.BooleanField(default=False)


    def can_be_deleted(self):
        """Check if the loan can be deleted (Not Finished)."""
        return self.status == 'Not Finished'

    def can_be_cancelled(self):
        """Check if the loan can be cancelled (Not Accepted)."""
        return self.status not in ['Accepted', 'Cancelled', 'Disbursed', 'Paid']
    def __str__(self):
        return f"{self.loan_type} loan for {self.applicant.first_name} {self.applicant.last_name}"

    def save(self, *args, **kwargs):
        if not self.tracking_id:
            self.tracking_id = f"{str(uuid.uuid4().int)[:4]}{self.loan_type[0]}"

        if self.id:
            latest_action = ActionNote.objects.filter(loan=self).order_by('-action_date').first()
            if latest_action:
                self.status = latest_action.action

        super().save(*args, **kwargs)


class Guarantor(models.Model):
    guarantor = models.ForeignKey(CustomUser, related_name='guarantors', on_delete=models.CASCADE)
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='guarantors')
    status_choices = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected')
    ]
    status = models.CharField(max_length=10, choices=status_choices, default='Pending')
    action_date = models.DateTimeField(null=True, blank=True)
    action_note = models.TextField(blank=True, null=True)



class MurabahaLoan(models.Model):
    loan = models.OneToOneField(Loan, on_delete=models.CASCADE, related_name='murabaha')
    asset_name = models.CharField(max_length=255)
    asset_value = models.DecimalField(max_digits=12, decimal_places=2, validators=[validate_positive])
    down_payment = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, validators=[validate_positive])
    profit_margin = models.DecimalField(max_digits=12, decimal_places=2, validators=[validate_positive], blank=True, null=True)
    total_loan_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    asset_image = models.ImageField(upload_to='murabaha/assets_images/', max_length=100, blank=True, null=True)
    created_at = models.DateField(auto_now=True)

    def save(self, *args, **kwargs):
        """Auto calculate the total loan amount"""
        print(self.asset_value)
        if self.down_payment is None:
            self.down_payment = Decimal(0)
        if self.profit_margin is None:
            self.profit_margin = Decimal(0)
        self.total_loan_amount = (self.asset_value + self.profit_margin) - self.down_payment

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Murabaha Loan for {self.loan.applicant.email}"

class QardHasanLoan(models.Model):
    loan = models.OneToOneField(Loan, on_delete=models.CASCADE, related_name='qard_hasan')
    total_loan_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[validate_positive])
    administrative_fee = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, validators=[validate_positive])
    created_at = models.DateField(auto_now=True)

    def clean(self):
        """Ensure total loan amount calculation is valid"""
      
        if self.total_loan_amount < 0:
            raise ValidationError("Loan amount must be positive.")
        
        if self.administrative_fee is not None and self.administrative_fee < 0:
            raise ValidationError("Administrative fee must be positive.")

    def __str__(self):
        return f"Qard Hasan Loan for {self.loan.applicant.email}"

from django.core.validators import RegexValidator
from django.db import models

class RepaymentSetting(models.Model):
    loan = models.OneToOneField(Loan, on_delete=models.CASCADE, related_name="repayment_settings")
    
    repayment_method = models.CharField(
        max_length=6, 
        choices=[
            ('salary', 'Salary Deduction'), 
            ('direct', 'Direct Deposit'), 
            ('both', 'Both Method')
        ]
    )

    # Validator to enforce "YYYY-MM" format
    month_year_validator = RegexValidator(
        regex=r'^\d{4}-(0[1-9]|1[0-2])$',  # Ensures only YYYY-MM format
        message="Date must be in YYYY-MM format."
    )

    repayment_start_date = models.CharField(
        max_length=7,  # "YYYY-MM" format (7 chars)
        validators=[month_year_validator]
    )

    repayment_end_date = models.CharField(
        max_length=7,
        blank=True,
        null=True,
        validators=[month_year_validator]
    )

    status = models.CharField(
        max_length=20,  
        choices=[
            ('Active', 'Active'), 
            ('Completed', 'Completed'), 
            ('Overdue', 'Overdue'),
            ('Not Started', 'Not Started')
        ], 
        default='Not Started'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Repayment Setting for loan {self.loan.loan_id}"

    @property
    def start_date(self):
        """
        Returns repayment_start_date as a date object (first day of the month).
        """

        if self.repayment_start_date:
            return datetime.strptime(self.repayment_start_date, "%Y-%m").date().replace(day=1)
        return None

    @property
    def end_date(self):
        """
        Returns repayment_end_date as a date object (last day of the month).
        """
        if self.repayment_end_date:
            # Find the last day of the month
            month = datetime.strptime(self.repayment_end_date, "%Y-%m")
            # Using `monthrange` to get the last day of the month
            from calendar import monthrange
            last_day = monthrange(month.year, month.month)[1]
            return month.replace(day=last_day)
        return None

class Repayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    repayment_date = models.DateTimeField()
    repayment_amount = models.DecimalField(max_digits=12, decimal_places=2)
    remaining_balance = models.DecimalField(max_digits=12, decimal_places=2)
    repayment_method = models.CharField(max_length=20, choices=[('Salary Deduction', 'Salary Deduction'), 
                                                               ('Direct Deposit', 'Direct Deposit'), 
                                                               ('both', 'Both Method')])
    status = models.CharField(max_length=20, choices=[('Paid', 'Paid'), 
                                                      ('Pending', 'Pending'), 
                                                      ('Overdue', 'Overdue')])
    repayment_setting = models.ForeignKey(RepaymentSetting, on_delete=models.CASCADE, related_name="repayments")

    def save(self, *args, **kwargs):
        """Automatically update the remaining balance and status upon saving"""
        # Calculate remaining balance
        if self.pk is None:  # New repayment
            self.remaining_balance = self.loan.total_loan_amount - self.repayment_amount
        else:  # Existing repayment
            self.remaining_balance = self.loan.total_loan_amount - sum(rep.repayment_amount for rep in self.repayment_setting.repayments.all())

        # Update repayment status based on remaining balance
        if self.remaining_balance <= 0:
            self.status = 'Paid'
        elif self.repayment_date > self.repayment_setting.repayment_end_date:
            self.status = 'Overdue'
        else:
            self.status = 'Pending'

        # Save the repayment
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Repayment for loan {self.loan.loan_id} on {self.repayment_date}"

class GracePeriodExtension(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    extension_request_date = models.DateTimeField(auto_now_add=True)
    extension_duration = models.IntegerField()  # max 3 months
    reason_for_extension = models.TextField()
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')])
    action_note = models.TextField(blank=True, null=True)
    action_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Extension Request for {self.loan.applicant.email}"


class LoanAgreement(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    agreement_signed_date = models.DateTimeField(auto_now_add=True)
    agreement_terms = models.TextField()
    status = models.CharField(max_length=20, choices=[('Signed', 'Signed'), ('Pending', 'Pending'), ('Rejected', 'Rejected')])

    def __str__(self):
        return f"Loan Agreement for {self.loan.applicant.email}"


class TransactionLog(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('Repayment', 'Repayment'),
        ('Loan Disbursement', 'Loan Disbursement'),
        ('Penalty', 'Penalty'),
    ]

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    transaction_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_description = models.TextField()
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)

    def __str__(self):
        return f"Transaction Log for {self.applicant.email} on {self.transaction_date}"



class LoanCommittee(models.Model):
    member = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='loan_committee_member')
    role = models.CharField(max_length=50, choices=[('Reviewer', 'Reviewer'), ('Approver', 'Approver')])
    committee_member_status = models.CharField(max_length=20, choices=[('Active', 'Active'), ('Inactive', 'Inactive')], blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Committee Member {self.member.email} ({self.role})"

class CommitteeAction(models.Model):
    committee_member = models.ForeignKey(LoanCommittee, on_delete=models.CASCADE, related_name="actions")
    action_date = models.DateTimeField(auto_now_add=True)
    action_taken = models.CharField(max_length=50, choices=[('Okay', 'Okay'), ('Not Okay', 'Not Okay'), 
                                                           ('Approved', 'Approved'), ('Disapproved', 'Disapproved')])
    action_reason = models.TextField()
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="committee_actions")

    def __str__(self):
        return f"Action by {self.committee_member.email} on Loan {self.loan_committee.loan.loan_id}"
