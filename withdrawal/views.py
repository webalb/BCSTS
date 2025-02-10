from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import EmployeeAccountDetails, WithdrawalCharge, EmployeeSavings
from .forms import EmployeeAccountForm, WithdrawalChargeForm
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ValidationError


# Admin check function
def is_admin(user):
    return user.groups.filter(name="admin").exists()

def is_employee(user):
    return user.groups.filter(name="Employee").exists()

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



# ==========================
# WITHDRAWAL CHARGE MODEL
# ==========================
@login_required
@user_passes_test(is_admin)
def withdrawal_charge_create(request):
    """Handles the creation of a new withdrawal charge."""
    charges = WithdrawalCharge.objects.all()
    if request.method == "POST":
        form = WithdrawalChargeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Withdrawal charge added successfully!")
            return redirect('withdrawal:charge_create')  # Redirect to the charge list page
    else:
        form = WithdrawalChargeForm()

    return render(request, "withdrawal/charge_form.html", {"form": form, 'charges': charges})


@login_required
@user_passes_test(is_admin)
def withdrawal_charge_delete(request, pk):
    """Delete a withdrawal charge."""
    charge = get_object_or_404(WithdrawalCharge, pk=pk)

    if request.method == "POST":
        charge.delete()
        messages.success(request, "Withdrawal charge deleted successfully!")
        return redirect('withdrawal:charge_create')

    return redirect('withdrawal:charge_create')


# 
# WITHDRAWAL REQUEST IMPLEMENTATION VIEWS
# 
from django.http import HttpResponseRedirect

@login_required
def withdrawal_policy(request):
    """ Display the withdrawal policy page with download option. """
    if request.method == "POST":
        return HttpResponseRedirect(reverse('withdrawal:request_form'))
    
    return render(request, "withdrawal/withdrawal_policy.html")


from .models import WithdrawalRequest
from .forms import WithdrawalRequestForm

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import WithdrawalRequest, EmployeeSavings
from .forms import WithdrawalRequestForm

@login_required
def withdrawal_request_form(request):
    """Form for employees to request withdrawal."""
    
    # Get or create EmployeeSavings for the logged-in user
    savings, _ = EmployeeSavings.objects.get_or_create(employee=request.user)
    
    available_to_withdraw = savings.available_for_withdrawal()
    total_saving = savings.total_to_withdraw

    if request.method == 'POST':
        form = WithdrawalRequestForm(request.POST, request.FILES)
        if form.is_valid():
            withdrawal_request = form.save(commit=False)
            withdrawal_request.employee = request.user  # Assign logged-in employee
            if withdrawal_request.withdrawal_type == 'partial':
                withdrawal_request.status = 'pending'

            try:
                withdrawal_request.save()  # Runs model validation
                messages.success(request, "Withdrawal request submitted successfully.")
                
                if withdrawal_request.withdrawal_type == 'complete':
                    return redirect('withdrawal:upload_documents', withdrawal_request.id)
                return redirect('withdrawal:completed')

            except ValidationError as e:
                messages.error(request, e)

        else:
            messages.error(request, "Please correct the errors below.")

    else:
        form = WithdrawalRequestForm()

    return render(
        request,
        "withdrawal/request_form.html",
        {
            "form": form,
            "available_to_withdraw": available_to_withdraw,
            "total_saving": total_saving,
        },
    )
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import WithdrawalRequest
from .forms import DocumentUploadForm

@login_required
def upload_document(request, withdrawal_request_id):
    withdrawal_request = get_object_or_404(WithdrawalRequest, id=withdrawal_request_id, employee=request.user)

    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES, withdrawal_request=withdrawal_request)
        if form.is_valid():
            withdrawal_request.document = form.cleaned_data['document']
            withdrawal_request.document_type = WithdrawalRequest.DOCUMENT_TYPES.get(withdrawal_request.reason)
            withdrawal_request.status = 'pending'
            withdrawal_request.save()

            messages.success(request, f"{withdrawal_request.document_type} uploaded successfully!")
            return redirect('withdrawal:completed')  # Redirect to the list of withdrawals
    else:
        form = DocumentUploadForm(withdrawal_request=withdrawal_request)

    return render(request, 'withdrawal/upload_document.html', {'form': form, 'withdrawal_request': withdrawal_request})

@login_required
def completed(request):
    """ Page showing the completion message after request submission. """
    return render(request, "withdrawal/completed.html")


@login_required
def cancel_withdrawal_request(request):
    """ employee intentionally cancelled the request"""
    if request.method == "POST":
        withdrawal_request_id = request.POST.get('withdrawal_request_id')
        withdrawal_request = get_object_or_404(WithdrawalRequest, id=withdrawal_request_id, employee=request.user)

        # Cancel the request
        withdrawal_request.cancel_request()

        # Redirect to the dashboard
        return redirect('dashboard')


@login_required
@user_passes_test(is_admin)
def withdrawal_requests_list(request):
    """ View to list all withdrawal requests categorized by status. """
    withdrawal_requests = WithdrawalRequest.objects.all()

    # Categorize requests
    cancelled_requests = withdrawal_requests.filter(status='cancelled')
    approved_requests = withdrawal_requests.filter(status='approved').exclude(transactions__isnull=False)  # Approved but not paid
    rejected_requests = withdrawal_requests.filter(status='rejected')
    pending_requests = withdrawal_requests.filter(status='pending')  # Pending (needs approval)
    complete_requests = withdrawal_requests.filter(transactions__isnull=False)  # Completed (has at least one related transaction)

    return render(request, 'withdrawal/withdrawal_requests_list.html', {
        'cancelled_requests': cancelled_requests,
        'complete_requests': complete_requests,
        'approved_requests': approved_requests,
        'rejected_requests': rejected_requests,
        'pending_requests': pending_requests,
    })

@login_required
def delete_withdrawal_request(request, withdrawal_request_id):
    """ View to delete a withdrawal request with confirmation. """
    withdrawal_request = get_object_or_404(WithdrawalRequest, id=withdrawal_request_id)

    if request.method == 'POST':  # Delete only if it's a POST request
        withdrawal_request.delete()
        messages.success(request, "Withdrawal request deleted successfully!")
    
    return redirect('withdrawal:withdrawal_requests_list')


from .forms import WithdrawalActionForm
from django.utils.timezone import now

@login_required
@user_passes_test(is_admin)
def approve_withdrawal_request(request, request_id):
    withdrawal_request = get_object_or_404(WithdrawalRequest, id=request_id)

    if request.method == 'POST':
        form = WithdrawalActionForm(request.POST, instance=withdrawal_request)
        if form.is_valid():
            withdrawal_request.status = 'approved'
            withdrawal_request.action_on = now()
            withdrawal_request.save()
            return redirect('withdrawal:withdrawal_requests_list')
    else:
        form = WithdrawalActionForm()

    return render(request, 'withdrawal/action_form.html', {
        'form': form,
        'withdrawal_request': withdrawal_request,
        'action': 'Approve'
    })

@login_required
@user_passes_test(is_admin)
def reject_withdrawal_request(request, request_id):
    withdrawal_request = get_object_or_404(WithdrawalRequest, id=request_id)

    if request.method == 'POST':
        form = WithdrawalActionForm(request.POST, instance=withdrawal_request)
        if form.is_valid():
            withdrawal_request.status = 'rejected'
            withdrawal_request.action_on = now()
            withdrawal_request.save()
            return redirect('withdrawal:withdrawal_requests_list')
    else:
        form = WithdrawalActionForm()

    return render(request, 'withdrawal/action_form.html', {
        'form': form,
        'withdrawal_request': withdrawal_request,
        'action': 'Reject'
    })

from .models import WithdrawalRequest, WithdrawalTransaction
from .forms import WithdrawalTransactionForm

@login_required
@user_passes_test(is_admin)
def process_payment(request, request_id):
    withdrawal_request = get_object_or_404(WithdrawalRequest, id=request_id)

    if withdrawal_request.is_paid:
        messages.warning(request, "This withdrawal request has already been processed.")
        return redirect('withdrawal:withdrawal_requests_list')

    if request.method == "POST":
        form = WithdrawalTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.request = withdrawal_request  # Link to the withdrawal request
            transaction.save()

            # Mark request as paid
            withdrawal_request.is_paid = True
            withdrawal_request.save()

            # Update Employee Savings
            withdrawal_request.employee.savings.update_savings()

            messages.success(request, "Transaction successfully processed.")
            return redirect('withdrawal:withdrawal_requests_list')
    else:
        form = WithdrawalTransactionForm(initial={'amount': withdrawal_request.amount})

    return render(request, 'withdrawal/process_withdrawal.html', {'form': form, 'request_data': withdrawal_request})

from django.shortcuts import render
from django.db.models import Sum
from .models import WithdrawalTransaction

@login_required
@user_passes_test(is_admin)
def admin_transactions(request):
    transactions = WithdrawalTransaction.objects.all().order_by('-transaction_date')
    total_withdrawn = transactions.aggregate(Sum('final_amount'))['final_amount__sum'] or 0

    context = {
        'transactions': transactions,
        'total_withdrawn': total_withdrawn
    }
    return render(request, 'withdrawal/admin_transactions.html', context)

from django.contrib.auth.decorators import login_required

@login_required
@user_passes_test(is_employee)
def employee_transactions(request):
    employee = request.user
    transactions = WithdrawalTransaction.objects.filter(request__employee=employee).order_by('-transaction_date')
    total_withdrawn = transactions.aggregate(Sum('final_amount'))['final_amount__sum'] or 0

    context = {
        'transactions': transactions,
        'total_withdrawn': total_withdrawn
    }
    return render(request, 'withdrawal/employee_transactions.html', context)

from django.shortcuts import get_object_or_404
from django.http import FileResponse, HttpResponse
from .models import WithdrawalTransaction
from .utils import generate_withdrawal_receipt

@login_required
@user_passes_test(is_employee)
def download_receipt(request, transaction_id):
    """ Generate and return the withdrawal receipt as a PDF. """

    transaction = get_object_or_404(WithdrawalTransaction, id=transaction_id, request__employee=request.user)
    
    if not transaction.request.is_paid:
        return HttpResponse("Receipt unavailable. Payment is not completed yet.", status=403)
    
    buffer = generate_withdrawal_receipt(transaction)
    response = FileResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{transaction.reference_number}.pdf"'
    
    return response
