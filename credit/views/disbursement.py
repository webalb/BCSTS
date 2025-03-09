from django.contrib.auth.decorators import login_required, user_passes_test
from credit.models import Credit, TransactionLog, Repayment
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from credit.utils.utils import *


def is_admin(user):
    return user.groups.filter(name="admin").exists()

def is_employee(user):
    return user.groups.filter(name="Employee").exists()



@login_required
@user_passes_test(is_admin)
def approved_credit_requests(request):
    approved_credits = Credit.objects.filter(status__in=['Approved', 'Accepted'])
    return render(request, 'credit/approved_credit_requests.html', {'approved_credits': approved_credits})

@login_required
@user_passes_test(is_admin)
def disburse_credit(request, tracking_id):
    credit = get_object_or_404(Credit, tracking_id=tracking_id, status__in=['Approved', 'Accepted'])
    
    if request.method == 'POST':
        receipt = request.FILES.get('transaction_receipt')
        repayment_start_month = request.POST.get('repayment_start_month')
        if receipt:
            amount = credit.amount_requested
            existing_transaction = TransactionLog.objects.filter(credit=credit, transaction_type='C').first()
            if existing_transaction and credit.status == 'Disbursed':
                messages.error(request, 'Credit is already disbursed.')
                return redirect('credit:credit_detail', tracking_id=credit.tracking_id)
            try:
                if not existing_transaction:
                    TransactionLog.objects.create(
                        credit=credit,
                        transaction_type='C',
                        amount=amount,
                        transaction_receipt=receipt
                    )
                credit.status = 'Disbursed'
                credit.repayment_start_month = repayment_start_month
                if credit.credit_type == 'Murabaha' and credit.repayment_period is not None:
                    credit.monthly_deduction = Decimal(credit.murabaha.selling_price) / Decimal(credit.repayment_period) # type: ignore
                elif credit.amount_requested is not None and credit.repayment_period is not None:
                    credit.monthly_deduction = Decimal(credit.amount_requested) / Decimal(credit.repayment_period)
                else:
                    messages.error(request, 'Invalid credit amount or repayment period.')
                    return redirect('credit:credit_detail', tracking_id=credit.tracking_id)
                credit.save()
            except ValidationError as e:
                messages.error(request, str(e))
                return redirect('credit:credit_detail', tracking_id=credit.tracking_id)
            heading = "Credit Disbursement Notification"
            body = f"Dear {credit.applicant.get_full_name()}, your credit request has been disbursed successfully."
            link = reverse('credit:create_credit_application')
            notify_applicant(credit, heading, body, link)
            messages.success(request, 'Credit has been successfully disbursed.')
            return redirect('credit:approved_credit_request')
        else:
            messages.error(request, 'No receipt uploaded.')
    
    return redirect('credit:credit_detail', tracking_id=credit.tracking_id)

@login_required
@user_passes_test(is_admin)
def disbursed_credits(request):
    disbursed_credits = Credit.objects.filter(status='Disbursed')

    return render(request, 'credit/repayment_request.html', {'disbursed_credits': disbursed_credits})

@login_required
@user_passes_test(is_admin)
def clear_credit(request, tracking_id):
    credit = get_object_or_404(Credit, tracking_id=tracking_id, status='Disbursed')
    
    if request.method == 'POST':
        amount_to_clear = request.POST.get('clear_amount')
        receipt = request.FILES.get('transaction_receipt')
        
        if amount_to_clear and receipt:
            try:
                amount_to_clear = Decimal(amount_to_clear)
                if amount_to_clear <= 0:
                    messages.error(request, 'Invalid amount to clear.')
                    return redirect('credit:credit_detail', tracking_id=credit.tracking_id)
                
                TransactionLog.objects.create(
                    credit=credit,
                    transaction_type='R',
                    amount=amount_to_clear,
                    transaction_receipt=receipt
                )
                Repayment.objects.create(
                    credit=credit,
                    amount=amount_to_clear,
                    repayment_method='D',
                )
                
                heading = "Credit Clearance Notification"
                body = f"Dear {credit.applicant.get_full_name()}, your credit has been cleared successfully. Amount cleared: NGN{amount_to_clear}."
                link = reverse('credit:create_credit_application')
                notify_applicant(credit, heading, body, link)
                
                messages.success(request, 'Credit has been successfully cleared. Amount cleared: NGN{amount_to_clear}')
                return redirect('credit:credit_detail', tracking_id=credit.tracking_id)
            except ValidationError as e:
                messages.error(request, str(e))
                return redirect('credit:credit_detail', tracking_id=credit.tracking_id)
        else:
            messages.error(request, 'Amount to clear or receipt not provided.')
    
    return redirect('credit:credit_detail', tracking_id=credit.tracking_id)


@login_required
@user_passes_test(is_employee)
def accept_or_reject(request, tracking_id):
    credit = get_object_or_404(Credit, tracking_id=tracking_id, status='Approved')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'accept':
            credit.status = 'Accepted'
            heading = "Credit Accepted Notification"
            body = f"Dear Admin, the credit request from {credit.applicant.get_full_name()} has been accepted."
        elif action == 'reject':
            credit.status = 'Cancelled'
            heading = "Credit Rejection Notification"
            body = f"Dear Admin, the credit request from {credit.applicant.get_full_name()} has been cancelled."
        else:
            messages.error(request, 'Invalid action.')
            return redirect('credit:create_credit_application')
        
        credit.save()
        link = reverse('credit:credit_detail', args=[credit.tracking_id]) # type: ignore
        notify_admins(heading, body, link) # type: ignore
        messages.success(request, f'Credit request has been {credit.status.lower()}.')
        return redirect('credit:create_credit_application')
    
    return render(request, 'credit/accept_or_reject.html', {'credit': credit})


@login_required
@user_passes_test(is_admin)
def credit_history(request):
    """
    Displays the credit history for the logged-in user, excluding pending, approved, accepted, and disbursed requests.
    """
    excluded_statuses = ['Pending', 'Approved', 'Accepted', 'Disbursed']
    credits = Credit.objects.filter(applicant=request.user).exclude(status__in=excluded_statuses).order_by('-date_applied')

    context = {
        'credits': credits,
    }
    return render(request, 'credit/credit_history.html', context)