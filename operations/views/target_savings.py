from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.timezone import now
from accounts.models import CustomUser
from operations.models import TargetSavings, TargetSavingsTransaction
from notification.services import NotificationService
from django.urls import reverse


def is_employee(user):
    return user.groups.filter(name="Employee").exists()

def is_admin(user):
    return user.groups.filter(name="Admin").exists()

from django.views.decorators.csrf import csrf_protect

@login_required
@user_passes_test(is_employee)
@csrf_protect  # Ensures CSRF validation
def member_target_savings_page(request):
    """Display the member's Target Savings page with details, transactions, and previous targets."""
    active_target = TargetSavings.objects.filter(member=request.user, status__in=['active', 'W-R']).first()
    previous_targets = TargetSavings.objects.filter(member=request.user, status='completed')

    
    if request.method == 'POST':
        if active_target:
            messages.info(request, "You already have an active target savings.")
        csrf_token = request.POST.get('csrfmiddlewaretoken')
        agree_terms = request.POST.get('agree_terms')
        
        if not csrf_token:
            messages.error(request, "Invalid CSRF token.")
        elif not agree_terms:
            messages.error(request, "You must agree to the terms and conditions.")
        else:
            TargetSavings.objects.create(member=request.user, status='active')
            NotificationService.send_notification(
                user=request.user,
                heading="Target Savings Created",
                message="Your target savings has been created successfully.",
                link=""
            )
            admin_users = CustomUser.objects.filter(groups__name='Admin')
            for admin in admin_users:
                NotificationService.send_notification(
                    user=admin,
                    heading="New Target Savings Created",
                    message=f"New target savings created by {request.user.username}.",
                    link=""
                )
            messages.success(request, "Target savings created successfully.")
            return redirect('member_target_savings_page')

    return render(request, 'operations/target/employee_target_page.html', {
        'active_target': active_target,
        'previous_targets': previous_targets,
    })


@login_required
@user_passes_test(is_employee)
@csrf_protect
def request_target_withdrawal(request, target_id):
    """Handles the request for a target savings withdrawal."""
    target = get_object_or_404(TargetSavings, id=target_id, member=request.user, status='active')

    if request.method == 'POST':
        target.status = 'W-R'  # Set status to Withdrawal Requested
        target.save()

        NotificationService.send_notification(
            user=request.user,
            heading="Target Withdrawal Requested",
            message="Your target savings withdrawal has been requested.",
            link=reverse('member_target_savings_page')
        )

        admin_users = CustomUser.objects.filter(groups__name='Admin')
        for admin in admin_users:
            NotificationService.send_notification(
                user=admin,
                heading="Target Withdrawal Request",
                message=f"Target withdrawal requested by {request.user.email}.",
                link=reverse("target_savings_detail", kwargs={'target_id': target.id})
            )

        messages.success(request, "Withdrawal request submitted successfully.")
        return redirect('member_target_savings_page')

    messages.error(request, "Invalid request.")
    return redirect('member_target_savings_page')

@login_required
@user_passes_test(is_admin)
def admin_target_savings_page(request):
    """Display the admin's Target Savings page with a list of all target savings."""
    target_savings = TargetSavings.objects.filter(status__in=["active", "W-R"]).all()

    return render(request, 'operations/target/admin_target_page.html', {
        'target_savings': target_savings,
    })

@login_required
@user_passes_test(is_admin)
def completed_target_savings(request):
    """Display the admin's Target Savings page with a list of all completed target savings."""
    completed_target_savings = TargetSavings.objects.filter(status="completed").all()

    return render(request, 'operations/target/admin_completed_target_page.html', {
        'completed_target_savings': completed_target_savings,
    })

from operations.forms import TargetTransactionForm, TargetWithdrawalPaymentForm
@login_required
@user_passes_test(is_admin)
def target_savings_detail(request, target_id):
    """Admin view to see transactions on a target savings, add new target amounts, and approve withdrawal requests."""
    target_savings = get_object_or_404(TargetSavings, id=target_id)
    transactions = TargetSavingsTransaction.objects.filter(target_savings=target_savings).order_by('-transaction_date')
    withdrawal_requests = target_savings.status == 'W-R'
    complete = target_savings.status == 'completed'
    transaction_form = TargetTransactionForm()
    withdrawal_form = TargetWithdrawalPaymentForm()

    if request.method == 'POST':
        if 'add_target' in request.POST:
            transaction_form = TargetTransactionForm(request.POST, request.FILES)
            if transaction_form.is_valid():
                transaction = transaction_form.save(commit=False)
                transaction.target_savings = target_savings
                transaction.transaction_type = "deposit"
                transaction.save()
                NotificationService.send_notification(
                    user=target_savings.member,
                    heading="New Target Savings Transaction",
                    message=f"Your target savings has been credited with NGN{transaction.amount} successfully.",
                    link=reverse("member_target_savings_page") 
                )
                messages.success(request, "Target savings amount added successfully.")
                return redirect('target_savings_detail', target_id=target_savings.id)
            else:
                messages.error(request, "Error adding target savings amount.")
        
        elif 'pay_withdrawal' in request.POST:
            withdrawal_form = TargetWithdrawalPaymentForm(request.POST, request.FILES)
            if withdrawal_form.is_valid():
                withdrawal = withdrawal_form.save(commit=False)
                withdrawal.transaction_type = 'withdrawal'
                withdrawal.target_savings = target_savings
                withdrawal.amount = target_savings.total_savings()
                withdrawal.save()
                target_savings.status = 'completed'
                target_savings.wthdrawed_at = now()
                target_savings.save()
                NotificationService.send_notification(
                    user=target_savings.member,
                    heading="Target Savings Withdrawal Paid",
                    message=f"Your target savings withdrawal request has been paid successfully.",
                    link=reverse("member_target_savings_page") 
                )
                messages.success(request, "Withdrawal request paid successfully.")
                return redirect('target_savings_detail', target_id=target_savings.id)
            else:
                messages.error(request, "Error processing withdrawal payment.")

    return render(request, 'operations/target/admin_target_detail.html', {
        'target_savings': target_savings,
        'transactions': transactions,
        'withdrawal_requests': withdrawal_requests,
        'transaction_form': transaction_form,
        'withdrawal_form': withdrawal_form,
        'complete': complete,
    })

@login_required
@user_passes_test(is_employee)
def member_target_detail(request, target_id):
    """Member view to see transactions on a target savings."""
    target_savings = get_object_or_404(TargetSavings, id=target_id)
    transactions = TargetSavingsTransaction.objects.filter(target_savings=target_savings).order_by('-transaction_date')

    return render(request, 'operations/target/member_target_detail_page.html', {
            'target_savings': target_savings,
            'transactions': transactions,
        })