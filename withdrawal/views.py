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
            return redirect('dashboard')
        else:
            messages.error(request, "Error adding account. Try again.")
    else:
        form = EmployeeAccountForm()

    return render(request, 'withdrawal/add_account.html', {'form': form, 'API_KEY': settings.PAYSTACK_SCRET_KEY})

@login_required
@user_passes_test(is_employee)
def delete_account(request, pk):
    """Delete an employee account"""
    account = get_object_or_404(EmployeeAccountDetails, pk=pk)
    if request.method == 'POST':
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
# from django.http import HttpResponseRedirect


@login_required
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

@login_required
@user_passes_test(is_employee)
def cancel_request(request, request_id):
    withdrawal = get_object_or_404(Withdrawals, id=request_id)

    # Ensure only pending requests can be canceled
    if withdrawal.status == 'pending' or withdrawal.status == 'approved':
        withdrawal.status = 'cancelled'
        withdrawal.action_date = timezone.now()
        withdrawal.save()
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
            messages.success(request, "Withdrawal request declined successfully.")

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
            messages.success(request, "Withdrawal request marked as paid successfully.")

        withdrawal.save()
    
    return redirect('withdrawal:admin_withdrawal_management')

def decline_request(request, request_id):
    pass
    # withdrawal = get_object_or_404(WithdrawalRequest, id=request_id)
    # if withdrawal.status == 'pending':
    #     withdrawal.status = 'declined'
    #     withdrawal.save()
    #     messages.error(request, "Withdrawal request declined.")
    # return redirect('withdrawal:admin_withdrawal_management')

def pay_request(request, request_id):
    pass
    # withdrawal = get_object_or_404(WithdrawalRequest, id=request_id)
    # if withdrawal.status == 'approved':
    #     withdrawal.status = 'paid'
    #     withdrawal.save()
    #     messages.success(request, "Withdrawal request marked as paid.")
    # return redirect('withdrawal:admin_withdrawal_management')

