from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import EmployeeAccountDetails, Charges, Withdrawals
from .forms import EmployeeAccountForm, WithdrawalChargeForm
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ValidationError
from operations.utils import get_employee_financial_summary, get_system_financial_summary
from decimal import Decimal
from django.utils import timezone
from notification.services import NotificationService
from notification.models import Notification

# Admin check function
def is_admin(user):
    return user.groups.filter(name="admin").exists()

def is_employee(user):
    return user.groups.filter(name="Employee").exists()



@login_required
@user_passes_test(is_employee)
def employee_withdrawal_management(request):
    employee = request.user
    withdrawal_request = Withdrawals.get_employee_withdrawal_request(employee=employee)
    withdrawal_history = Withdrawals.get_employee_withdrawal_history(employee=employee)
    financial_summary = get_employee_financial_summary(employee)
    charge = Charges.get_current_charge()
    context = {
        "withdrawal_request": withdrawal_request,
        "withdrawal_history": withdrawal_history,
        "savings_balance": financial_summary["savings_balance"],
        "total_withdrawn": financial_summary["total_withdrawn"],
        "charge": charge,
    }

    return render(request, "withdrawal/employee_withdrawals.html", context)

@login_required
@user_passes_test(is_admin)
def admin_withdrawal_management(request):
    withdrawal_requests = Withdrawals.get_withdrawal_requests()
    withdrawal_history = Withdrawals.get_withdrawal_history()
    financial_summary = get_system_financial_summary()
    charge = Charges.get_current_charge()
    context = {
        "withdrawal_requests": withdrawal_requests,
        "withdrawal_history": withdrawal_history,
        "savings_balance": financial_summary["total_system_savings_balance"],
        "total_withdrawn": financial_summary["total_withdrawn"],
        "charge": charge,
    }
    
    return render(request, "withdrawal/admin_withdrawals.html", context)

@login_required
@user_passes_test(is_employee)
def add_account(request):
    """Handles account form submission."""
    if request.method == 'POST':
        form = EmployeeAccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.employee_id = request.user.id
            account.save()
            messages.success(request, "Bank account added successfully!")
            NotificationService.send_notification(
                request.user, 
                "Bank Account Added",
                "Your bank account has been successfully added to your profile.",
                link=reverse("dashboard"),  # Or a more specific link if needed
                notification_type=Notification.NotificationType.IN_APP
            )
            return redirect('dashboard')
        else:
            print(form.errors)
            messages.error(request, "Error adding account. Try again.")
    else:
        form = EmployeeAccountForm()

    return render(request, 'accounts/settings.html', {'bank_form': form, 'API_KEY': settings.PAYSTACK_SCRET_KEY})

@login_required
@user_passes_test(is_employee)
def delete_account(request, pk):
    """Delete an employee account"""
    account = get_object_or_404(EmployeeAccountDetails, pk=pk)
    if request.method == 'POST':
        NotificationService.send_notification(
            account.employee,  # Get the employee from the account
            "Bank Account Removed",
            "Your bank account details have been removed. You can add a new bank account in your profile.",
            link=reverse("settings"),  # Or a more specific link
            notification_type=Notification.NotificationType.IN_APP
        )
        account.delete()
        messages.success(request, "Bank account deleted successfully.")
        return redirect('dashboard')
    return render(request, 'withdrawal/delete_account.html', {'account': account})



# # ==========================
# # WITHDRAWAL CHARGE MODEL
# # ==========================
from django.http import JsonResponse
from django.db import transaction

@login_required
@user_passes_test(is_admin)
def charge_management(request):
    """Admin view to manage withdrawal charges."""
    current_charge = Charges.get_current_charge()
    charge_history = Charges.objects.all().order_by("-created_at")  # List all charges

    context = {
        "current_charge": current_charge,
        "charge_history": charge_history,
    }
    return render(request, "withdrawal/charge_form.html", context)


@login_required
@user_passes_test(is_admin)
def update_charge(request):
    """Handles charge update and re-renders the charge form."""
    if request.method == "POST":
        charge_percentage = request.POST.get("charge_percentage")

        if not charge_percentage:
            return redirect("withdrawal:charge_management")
        with transaction.atomic():
            Charges.objects.filter(status="current").update(status="deprecated")  # Deprecate old charge
            new_charge = Charges.objects.create(charge_percentage=charge_percentage, status="current")

        return redirect("withdrawal:charge_management")

    return redirect("withdrawal:charge_management")
# # =======================================
# # WITHDRAWAL REQUEST IMPLEMENTATION VIEWS
# # ======================================


@login_required
@user_passes_test(is_employee)
def withdrawal_request(request):
    """Processes employee withdrawal request and redirects to the management page."""
    if request.method == "POST":
        amount_requested = request.POST.get("amount_requested")

        # Ensure valid amount
        if not amount_requested or Decimal(amount_requested) <= 0:
            messages.error(request, "Invalid withdrawal amount.")
            return redirect("withdrawal:employee_withdrawal_management")

        user = request.user  # Logged-in employee

        # Get current charge percentage
        charge_obj = Charges.get_current_charge()
        charge_percentage = Decimal(charge_obj.charge_percentage) if charge_obj else Decimal("0.00")
        
        # Calculate charges
        charges_applied = (Decimal(amount_requested) * charge_percentage) / 100
        total_deduction = Decimal(amount_requested) + charges_applied  # Total amount to be deducted

        savings_balance = get_employee_financial_summary(user)["savings_balance"]
        # Ensure withdrawal + charges do not exceed the employee's saving balance
        if savings_balance and total_deduction > savings_balance:
            messages.error(request, "Insufficient savings balance for this withdrawal.")
            return redirect("withdrawal:employee_withdrawal_management")

        # Save withdrawal request
        Withdrawals.objects.create(
            employee=user,
            amount_requested=Decimal(amount_requested),
            charges_applied=charges_applied,
            status="pending",
        )

        messages.success(request, "Withdrawal request submitted successfully.")
        return redirect("withdrawal:employee_withdrawal_management")

    return redirect("withdrawal:employee_withdrawal_management")  # Fallback for GET request

from django.contrib.auth.models import Group


@login_required
@user_passes_test(is_employee)
def cancel_request(request, request_id):
    withdrawal = get_object_or_404(Withdrawals, id=request_id)

    # Ensure only pending requests can be canceled
    if withdrawal.status == 'pending' or withdrawal.status == 'approved':
        withdrawal.status = 'cancelled'
        withdrawal.action_date = timezone.now()
        withdrawal.save()
        admin_group = Group.objects.get(name='Admin')
        admins = admin_group.user_set.all()

        for admin in admins:
            NotificationService.send_notification(
                admin,
                "Withdrawal Request Cancelled",
                f"Withdrawal request #{withdrawal.id} has been cancelled.",
                link=reverse("withdrawal:admin_withdrawal_management"),
                notification_type=Notification.NotificationType.IN_APP
            )
        messages.success(request, "Withdrawal request has been canceled.")
    else:
        messages.error(request, "You can only cancel pending or approved requests.")

    return redirect('withdrawal:employee_withdrawal_management')  # Adjust redirect URL

def approve_request(request, request_id):
    
    withdrawal = get_object_or_404(Withdrawals, id=request_id)
    if withdrawal.status == 'pending':
        withdrawal.status = 'approved'
        withdrawal.action_date = timezone.now()
        withdrawal.save()
        # send notification to the requester (withdrawal.employee)

        NotificationService.send_notification(
            withdrawal.employee,  # Send to the employee who requested the withdrawal
            "Withdrawal Request Approved",
            f"Your withdrawal request #{withdrawal.id} has been approved.",  # Or withdrawal.pk
            link=reverse("withdrawal:employee_withdrawal_management"),  # Or a more specific link to withdrawal details
            notification_type=Notification.NotificationType.IN_APP
        )
        messages.success(request, "Withdrawal request approved successfully.")
    return redirect('withdrawal:admin_withdrawal_management')

from django.utils.timezone import now

def update_withdrawal_status(request):
    if request.method == 'POST':
        withdrawal_id = int(request.POST.get('request_id'))
        action = request.POST.get('action')

        withdrawal = get_object_or_404(Withdrawals, id=withdrawal_id)

        if action == 'decline':
            if withdrawal.status != Withdrawals.Status.PENDING:
                messages.error(request, "Invalid status for declined.")
                return redirect('withdrawal:admin_withdrawal_management')

            reason = request.POST.get('action_note')
            withdrawal.status = Withdrawals.Status.DECLINED
            withdrawal.action_note = reason
            withdrawal.action_date = now()
            NotificationService.send_notification(
                withdrawal.employee,  # Send to the employee who requested the withdrawal
                "Withdrawal Request Declined",
                f"Your withdrawal request #{withdrawal.id} has been Declined.",  # Or withdrawal.pk
                link=reverse("withdrawal:employee_withdrawal_management"),  # Or a more specific link to withdrawal details
                notification_type=Notification.NotificationType.IN_APP
            )
            messages.success(request, "Withdrawal request declined.")

        elif action == 'pay':
            if withdrawal.status not in [Withdrawals.Status.PENDING, Withdrawals.Status.APPROVED]:
                messages.error(request, "Invalid status for payment.")
                return redirect('withdrawal:admin_withdrawal_management')

            payment_reference = request.POST.get('payment_reference')
            withdrawal.payment_reference = payment_reference
            withdrawal.payment_date = now()

            if withdrawal.status == Withdrawals.Status.PENDING:
                withdrawal.action_date = now()

            withdrawal.status = Withdrawals.Status.PAID
            withdrawal.total_amount_withdrawn = withdrawal.amount_requested + withdrawal.charges_applied
            NotificationService.send_notification(
                withdrawal.employee,  # Send to the employee who requested the withdrawal
                "Withdrawal Request Paid",
                f"Your withdrawal request #{withdrawal.id} has been Paid.",  # Or withdrawal.pk
                link=reverse("withdrawal:employee_withdrawal_management"),  # Or a more specific link to withdrawal details
                notification_type=Notification.NotificationType.IN_APP
            )
            messages.success(request, "Withdrawal request marked as paid successfully.")

        withdrawal.save()
    
    return redirect('withdrawal:admin_withdrawal_management')
