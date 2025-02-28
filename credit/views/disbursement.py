from django.http import JsonResponse

from django.contrib.auth.decorators import login_required, user_passes_test
from credit.models import Credit, TransactionLog
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
    approved_credits = Credit.objects.filter(status='Approved')
    return render(request, 'credit/approved_credit_requests.html', {'approved_credits': approved_credits})

@login_required
@user_passes_test(is_admin)
def disburse_credit(request, tracking_id):
    credit = get_object_or_404(Credit, tracking_id=tracking_id, status='Approved')
    
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
                if credit.amount_requested is not None and credit.repayment_period is not None:
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
            link = redirect('credit:create_credit_application')
            notify_applicant(credit, heading, body, link)
            messages.success(request, 'Credit has been successfully disbursed.')
            return redirect('credit:approved_credit_request')
        else:
            messages.error(request, 'No receipt uploaded.')
    
    return redirect('credit:credit_detail', tracking_id=credit.tracking_id)