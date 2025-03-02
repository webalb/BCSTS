from accounts.models import CustomUser
from decimal import Decimal
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum
from django.db import models, transaction
from django.utils.timezone import localtime


class Charges(models.Model):
    """Defines the charges for withdrawals."""
    charge_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=12,
        choices=[('current', 'Current'), ('deprecated', 'Deprecated')],
        default='current'
    )

    def save(self, *args, **kwargs):
        """Ensure only one charge has 'current' status at a time."""
        with transaction.atomic():  # Prevents race conditions
            if self.status == 'current':
                Charges.objects.filter(status='current').update(status='deprecated')
            super().save(*args, **kwargs)

    @classmethod
    def get_current_charge(cls):
        """Returns the active charge percentage."""
        return cls.objects.filter(status='current').first()

    def __str__(self):
        return f"Charge: {self.charge_percentage}% ({self.status})"

class Withdrawals(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        APPROVED = 'approved', _('Approved')
        DECLINED = 'declined', _('Declined')
        CANCELLED = 'cancelled', _('Cancelled')
        PAID = 'paid', _('Paid')

    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount_requested = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    request_date = models.DateTimeField(auto_now_add=True)
    action_date = models.DateTimeField(null=True, blank=True)
    action_note = models.TextField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    charges_applied = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount_withdrawn = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"{self.employee.email} - {self.amount_requested} ({self.status})"

    @classmethod
    def get_employee_total_paid_withdrawals(cls, employee):
        """
        Returns the total amount of paid withdrawals for a specific employee.
        """
        total_paid = cls.objects.filter(employee=employee, status=cls.Status.PAID).aggregate(total=Sum('total_amount_withdrawn'))['total']
        return total_paid or Decimal('0.00')
    
    @classmethod
    def get_employee_withdrawal_request(cls, employee):
        """
        Returns the latest pending or approved withdrawal request for an employee.
        """
        return cls.objects.filter(employee=employee, status__in=[cls.Status.PENDING, cls.Status.APPROVED]).first()

    @classmethod
    def get_employee_withdrawal_history(cls, employee):
        """
        Returns all paid withdrawals for a specific employee.
        """
        return cls.objects.filter(employee=employee,  status__in=[cls.Status.PAID, cls.Status.DECLINED, cls.Status.CANCELLED])

    @classmethod
    def get_withdrawal_requests(cls):
        """
        Returns all withdrawals that are not yet paid.
        """
        return cls.objects.filter(status__in=[cls.Status.PENDING, cls.Status.APPROVED])

    @classmethod
    def get_withdrawal_history(cls):
        """
        Returns all paid withdrawals in the system.
        """
        return cls.objects.filter(status__in=[cls.Status.PAID, cls.Status.DECLINED, cls.Status.CANCELLED])

    @classmethod
    def get_system_total_paid_withdrawals(cls):
        """
        Returns the total amount of paid withdrawals across the system.
        """
        total_paid = cls.objects.filter(status=cls.Status.PAID).aggregate(total=Sum('total_amount_withdrawn'))['total']
        return total_paid or Decimal('0.00')

    def save(self, *args, **kwargs):
        if self.payment_date:
            self.payment_date = localtime(self.payment_date)
        super().save(*args, **kwargs)


class EmployeeAccountDetails(models.Model):
    """Stores employee bank account details for payments."""
    employee = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="account_details")
    bank_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=20)
    account_holder_name = models.CharField(max_length=255)

    def __str__(self):
        return f"Account Details for {self.employee.nitda_id} - {self.bank_name}"
