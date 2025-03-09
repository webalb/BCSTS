from accounts.models import CustomUser as User
from accounts.models import CustomUser
from decimal import Decimal
from datetime import timedelta, date
from django.urls import reverse
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.http import Http404

from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.utils.timezone import now
from django.db.models import Sum, Q

from operations.models import ContributionRecord, ContributionSetting, ContributionSettingHistory, ContributionChangeRequest
from operations.forms import ContributionSettingAdminForm
from withdrawal.models import Withdrawals
from .contribution import calculate_contribution_durations

from operations.utils import get_system_financial_summary  # Importing your utility function
from notification.services import NotificationService
from notification.models import Notification
from credit.utils.utils import get_system_credit_summary

# Admin check function
def is_admin(user):
    return user.groups.filter(name="Admin").exists()

@login_required
def redirect_user(request):
    """Redirect users based on their role."""
    if request.user.groups.filter(name="Admin").exists():
        return redirect('admin_dashboard')  # Redirect to admin dashboard
    elif request.user.groups.filter(name="Employee").exists():
        return redirect('dashboard')  # Redirect to employee dashboard
    else:
        return redirect('login')  # Default case if no role assigned



@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin dashboard showing employee contributions overview."""
    employees = User.objects.exclude(Q(is_superuser=True) | Q(groups__name="admin"))
    total_employees = employees.count()

    today = timezone.now().date()
    current_month, current_year = today.month, today.year

    # Check if contributions for the current month exist
    contributions_exist = ContributionRecord.objects.filter(year=current_year, month=current_month).exists()

    # Get system-wide financial summary
    financial_summary = get_system_financial_summary()
    credit_summary = get_system_credit_summary()

    # Fetch latest 5 contributions
    latest_contributions = ContributionRecord.objects.order_by('-created_at')[:5]

    # Monthly contributions from ContributionSetting model
    monthly_contributions = ContributionSetting.objects.aggregate(Sum('amount'))['amount__sum'] or Decimal(0.00)

    # Employee contributions data
    employee_contributions = []


    for employee in employees:
        total_contributed = ContributionRecord.objects.filter(employee=employee).aggregate(Sum('amount'))['amount__sum'] or Decimal(0.00)
        employee_contributions.append({
            'employee': employee,
            'total_contributed': total_contributed,
            'contributions': ContributionRecord.objects.filter(employee=employee)
        })


    # Context for template rendering
    context = {
        'employees': employees,
        'total_employees': total_employees,
        'contributions_exist': contributions_exist,
        'employee_contributions': employee_contributions,
        'latest_contributions': latest_contributions,
        'today': today,
        'monthly_contributions': monthly_contributions,

        # Financial summary from utils
        'total_amount_raised': financial_summary["total_system_contributions"],
        'total_withdrawn': financial_summary["total_withdrawn"],
        'total_remained': financial_summary["total_remained_balance"],
        'saving_balance': financial_summary["total_system_savings_balance"],
        'investment_balance': financial_summary["total_system_investment_balance"],
        'credit_summary':credit_summary,
    }

    return render(request, 'operations/admin_dashboard.html', context)
# ================================
# ||| RECORD COTRIBUTION VIEWS |||
# ================================
    
# used
@login_required
@user_passes_test(is_admin)
def record_all_contributions(request):
    """Admin triggers all employee contribution deductions for the current month."""
    today = timezone.now().date()
    
    # Ensure today is 25th or later
    if today.day < int(settings.SALARY_PAYMENT_DATE):
        messages.warning(request, f"You can only record contributions on or after the {settings.SALARY_PAYMENT_DATE}th of the month.")
        return redirect(reverse("manage_contributions"))

    # Check if contributions for the current month already exist
    current_month = today.month
    current_year = today.year
    contributions_exist = ContributionRecord.objects.filter(
        year=current_year, 
        month=current_month
    ).exists()

    if contributions_exist:
        messages.warning(request, "All contributions for this month have already been recorded.")
        return redirect(reverse("manage_contributions"))

    # If conditions are met, record contributions
    records_created = ContributionRecord.bulk_record_contributions()
    
    if records_created > 0:
        messages.success(request, f"Successfully recorded {records_created} contributions for this month.")
    else:
        messages.warning(request, "No employee contributions were recorded.")

    return redirect(reverse("manage_contributions"))

@login_required
@user_passes_test(is_admin)
def record_individual_contribution(request, employee_id):
    """Allow admin to record a contribution for a single employee."""
    selected_month = now().month
    selected_year = now().year
    employee = get_object_or_404(CustomUser, id=employee_id, contribution_setting__isnull=False)

    # Check if contribution already exists
    if ContributionRecord.objects.filter(employee=employee, month=selected_month, year=selected_year).exists():
        messages.warning(request, f"Contribution for {employee.nitda_id} already recorded.")
    else:
        ContributionRecord.objects.create(
            employee=employee,
            amount=employee.contribution_setting.amount, # type: ignore
            month=selected_month,
            year=selected_year,
            status='Paid'
        )
        message=f"Dear {employee.get_full_name},\n\nYour monthly contribution of {employee.contribution_setting.amount} has been recorded for {selected_month}/{selected_year}.", # type: ignore
        NotificationService.send_notification(
            employee,
            heading="Monthly Contribution Deducted",
            message=message,
            link=reverse("dashboard"),  
            notification_type=Notification.NotificationType.IN_APP
        )
        messages.success(request, f"Contribution recorded for {employee.nitda_id}.")

    return redirect('manage_contributions')


@login_required
@user_passes_test(is_admin)
def record_all_missing_contributions(request):
    """Record contributions for all employees who are missing them for the current month."""
    selected_month = now().month
    selected_year = now().year

    missing_employees = CustomUser.objects.filter(
        contribution_setting__isnull=False,
        date_joined__year__lte=selected_year,
        date_joined__month__lte=selected_month
    ).exclude(
        contribution_records__month=selected_month,
        contribution_records__year=selected_year
    )

    records_created = 0

    for employee in missing_employees:
        ContributionRecord.objects.create(
            employee=employee,
            amount=employee.contribution_setting.amount, # type: ignore
            month=selected_month,
            year=selected_year,
            status='pending'
        )
        message=f"Dear {employee.get_full_name},\n\nYour monthly contribution of {employee.contribution_setting.amount} has been recorded for {selected_month}/{selected_year}.", # type: ignore
        NotificationService.send_notification(
            employee,
            heading="Monthly Contribution Deducted",
            message=message,
            link=reverse("dashboard"),  
            notification_type=Notification.NotificationType.IN_APP
        )
        records_created += 1

    if records_created > 0:
        messages.success(request, f"Successfully recorded {records_created} contributions.")
    else:
        messages.warning(request, "No new contributions were recorded.")

    return redirect('manage_contributions')


# =======================================
# ||| END OF RECORD COTRIBUTION VIEWS |||
# =======================================

from django.db.models import Max, Count, OuterRef, Subquery, Exists
from django.utils.timezone import now

@login_required
@user_passes_test(is_admin)
def manage_contributions(request):
    """View to manage contributions for a specific month and year."""
    
    # Fetch available months and years from database
    available_contributions = ContributionRecord.objects.values_list("month", "year").distinct()
    available_months = sorted(set(month for month, _ in available_contributions))
    available_years = sorted(set(year for _, year in available_contributions), reverse=True)

    # Default to latest year & month if none selected
    latest_contribution = ContributionRecord.objects.aggregate(latest_year=Max('year'), latest_month=Max('month'))
    default_year = latest_contribution['latest_year'] or now().year
    default_month = latest_contribution['latest_month'] or now().month
    if default_month > now().month and default_year == now().year:
        default_month = now().month

    selected_month = int(request.GET.get('month', default_month))
    selected_year = int(request.GET.get('year', default_year))

    # Get all recorded contributions for the selected month and year
    contributions = ContributionRecord.objects.filter(
        month=selected_month, year=selected_year
    )

    # Subquery to check if a user has a contribution record for the selected month & year
    existing_contributions = ContributionRecord.objects.filter(
        employee=OuterRef('pk'), month=selected_month, year=selected_year
    ).values('id')

    # Query employees who have contribution settings but no record for the selected month/year
    missing_contributions = CustomUser.objects.filter(
        contribution_setting__isnull=False,  # Ensure they have a contribution setting
        contribution_setting__updated_at__year__lte=selected_year,
        contribution_setting__updated_at__month__lte=selected_month
    ).annotate(
        has_contribution=Exists(existing_contributions)
    ).filter(
        has_contribution=False  # Employees who have settings but no record
    )

    # Check if contributions have been recorded for the selected month and year
    contributions_recorded = ContributionRecord.is_contribution_recorded_for_month(selected_month, selected_year)

    # Check if today is the salary payment date
    salary_payment_date = settings.SALARY_PAYMENT_DATE
    is_salary_payment_day = date.today().day >= int(salary_payment_date)

    context = {
        "contributions": contributions,
        "missing_contributions": missing_contributions,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "available_months": available_months,
        "available_years": available_years,
        "today": date.today(),
        'is_salary_payment_day': is_salary_payment_day,
        'salary_payment_date': salary_payment_date,
        "contributions_recorded": contributions_recorded,
    }
    
    return render(request, "operations/contributions/manage_contributions.html", context)


# used - SETTINGS
@login_required
@user_passes_test(is_admin)
def manage_employee_contributions(request):
    """Admin view to list all employees' contribution settings and those without settings."""
    
    all_employees = CustomUser.objects.exclude(Q(is_superuser=True) | Q(groups__name="Admin")).distinct()

    # Get employees with contribution settings
    contribution_settings = ContributionSetting.objects.select_related('employee')

    # Identify employees without contribution settings
    employees_without_settings = all_employees.exclude(id__in=contribution_settings.values_list('employee_id', flat=True))
    pending_requests = ContributionChangeRequest.objects.filter(status="pending")

    return render(request, 'operations/contributions/employee_contribution_setting.html', {
        'contribution_settings': contribution_settings,
        'employees_without_settings': employees_without_settings,
        'pending_requests': pending_requests,
    })


# used - SETTINGS
@login_required
@user_passes_test(is_admin)
def create_contribution_setting(request, employee_id):
    """Creates a new contribution setting for a specific employee."""
    employee = get_object_or_404(CustomUser, id=employee_id)

    # Prevent duplicate creation
    if ContributionSetting.objects.filter(employee=employee).exists():
        messages.error(request, "Contribution setting already exists for this employee.")
        return redirect('manage_employee_contributions')

    if request.method == 'POST':
        form = ContributionSettingAdminForm(request.POST)
        if form.is_valid():
            contribution_setting = form.save(commit=False)
            contribution_setting.employee = employee  # Assign the employee (Crucial)
            
            contribution_setting.save()
            message=f"Dear {employee.get_full_name},\n\nYour monthly contribution is updated.",
            NotificationService.send_notification(
                employee,
                heading="Contribution Setting Updated",
                message=message,
                link=reverse("contribution_setting_history"),  
                notification_type=Notification.NotificationType.IN_APP
            )
            messages.success(request, "Contribution setting created successfully.")
            return redirect('manage_employee_contributions')
    else:
        form = ContributionSettingAdminForm()  # No initial here

    return render(request, 'operations/contributions/contribution_setting.html', {'form': form, 'employee': employee})  # Pass employee to the template

# used - SETTINGS
# Admin view to update an existing contribution setting
@login_required
@user_passes_test(is_admin)
def update_contribution_setting(request, pk):
    """Updates an existing contribution setting for an employee."""
    contribution_setting = get_object_or_404(ContributionSetting, pk=pk)
    employee = contribution_setting.employee  # Get the employee (Important)

    if request.method == 'POST':
        form = ContributionSettingAdminForm(request.POST, instance=contribution_setting)
        if form.is_valid():
            form.save()  # No need to assign employee again, it's already linked
            message=f"Dear {employee.get_full_name},\n\nYour monthly contribution is updated.",
            NotificationService.send_notification(
                employee,
                heading="Contribution Setting Updated",
                message=message,
                link=reverse("contribution_setting_history"),  
                notification_type=Notification.NotificationType.IN_APP
            )
            messages.success(request, "Contribution setting updated successfully.")
            return redirect('manage_employee_contributions')
    else:
        form = ContributionSettingAdminForm(instance=contribution_setting)

    return render(request, 'operations/contributions/contribution_setting.html', {'form': form, 'employee': employee})  # Pass employee to the template

# used - SETTINGS
@login_required
@user_passes_test(is_admin)
def delete_contribution_setting(request, pk):
    """Deletes an employee's contribution setting."""
    contribution_setting = get_object_or_404(ContributionSetting, pk=pk)
    contribution_setting.delete()
    messages.success(request, "Contribution setting deleted successfully.")
    return redirect('manage_employee_contributions')



@login_required
@user_passes_test(is_admin)
def admin_contribution_history(request, employee_id):
    records = calculate_contribution_durations(employee_id)
    return render(request, 'operations/contributions/contribution_history.html', {'records': records})

@login_required
@user_passes_test(is_admin)
def delete_contribution_history(request, record_id):
    """ Delete a specific contribution setting history record. """
    
    try:
        # Fetch the record
        record = ContributionSettingHistory.objects.get(id=record_id)
        employee_id = record.contribution_setting.employee.id # type: ignore
        record.delete()
        messages.success(request, 'Contribution history record deleted successfully.')
    except ContributionSettingHistory.DoesNotExist:
        raise Http404("Contribution history record does not exist.")
    
    return redirect('admin_contribution_history', employee_id=employee_id)  # Redirect back to the history page

# RECORD
@login_required
@user_passes_test(is_admin)
def delete_contribution(request, contribution_id):
    """Allow admin to delete a specific contribution record."""
    contribution = get_object_or_404(ContributionRecord, id=contribution_id)
    contribution.delete()
    messages.success(request, "Contribution record deleted successfully.")
    return redirect('manage_contributions')

@login_required
@user_passes_test(is_admin)
def process_contribution_request(request, request_id, action):
    """Admin approves or rejects a request."""
    change_request = get_object_or_404(ContributionChangeRequest, id=request_id)

    if action == "approve":
        # Update the user's ContributionSetting
        contribution_setting, created = ContributionSetting.objects.get_or_create(employee=change_request.employee)
        old_amount = contribution_setting.amount
        contribution_setting.amount = change_request.requested_amount
        contribution_setting.save()

        change_request.status = "approved"
        employee = change_request.employee
        message = f"Dear {employee.get_full_name()},\n\nYour monthly contribution has been updated to ₦{change_request.requested_amount:,.2f}."

        NotificationService.send_notification(
            employee,
            heading="Contribution Amount Request Approved",
            message=message,
            link=reverse("contribution_setting_history"),
            notification_type=Notification.NotificationType.IN_APP  # Assuming this is the correct way to access the enum
        )
        messages.success(request, f"Request approved. Contribution updated from ₦{old_amount:,.2f} to ₦{change_request.requested_amount:,.2f}.")

    elif action == "reject":
        change_request.status = "rejected"
        employee = change_request.employee
        message = f"Dear {employee.get_full_name()},\n\nYour request to change your monthly contribution to ₦{change_request.requested_amount:,.2f} has been rejected."

        NotificationService.send_notification(
            employee,
            heading="Contribution Amount Request Rejected",
            message=message,
            link=reverse("contribution_setting_history"),
            notification_type=Notification.NotificationType.IN_APP
        )
        messages.warning(request, "Request has been rejected.")

    change_request.reviewed_at = timezone.now()
    change_request.reviewed_by = request.user
    change_request.save()

    return redirect("manage_employee_contributions")
from django.http import JsonResponse
from django.utils.timezone import now
from django.db.models import Sum
from datetime import datetime, timedelta
from credit.models import Credit, Repayment
from django.conf import settings

@login_required
@user_passes_test(is_admin)
def get_monthly_contributions(request):
    """Fetch total contributions and total withdrawals for the last 9 months."""
    today = now().date()
    last_9_months = [(today - timedelta(days=30 * i)).strftime('%b') for i in range(8, -1, -1)]

    contributions = []
    withdrawals = []
    credits = []
    repayments = []
    
    for i in range(8, -1, -1):
        month_date = today - timedelta(days=30 * i)
        month = month_date.month
        year = month_date.year

        # Sum contributions for each month
        total_contributions = ContributionRecord.objects.filter(
            month=month, year=year
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Sum withdrawals for each month (only PAID withdrawals)
        total_withdrawals = Withdrawals.objects.filter(
            payment_date__month=month, payment_date__year=year,  status=Withdrawals.Status.PAID
        ).aggregate(total=Sum('total_amount_withdrawn'))['total'] or Decimal('0.00')

        # Sum disbursed credits for each month
        disbursed_credits = Credit.objects.filter(
            Q(status='Repaid') | Q(status='Disbursed'), date_applied__month=month, date_applied__year=year
        ).aggregate(total=Sum('amount_requested'))['total'] or Decimal(0.00)
        
        repayment_credits = Repayment.objects.filter(
            repayment_date__month=month, repayment_date__year=year
        ).aggregate(total=Sum('amount'))['total'] or Decimal(0.00)

        repayments.append(float(repayment_credits))  
        credits.append(float(disbursed_credits))  # Convert Decimal to float
        contributions.append(float(total_contributions))  # Convert Decimal to float
        withdrawals.append(float(total_withdrawals))  # Convert Decimal to float

    return JsonResponse({'months': last_9_months, 'contributions': contributions, 'withdrawals': withdrawals, 'credits': credits, 'repayments': repayments})


@login_required
@user_passes_test(is_admin)
def view_employee_contributions(request, employee_id):
    employee = get_object_or_404(CustomUser, id=employee_id)
    contributions = ContributionRecord.objects.filter(employee=employee).order_by('-year', '-month')
    
    total_contributed = contributions.aggregate(total=Sum("amount"))["total"] or 0
    
    context = {
        'employee': employee,
        'contributions': contributions,
        'total_contributed': total_contributed,
    }
    
    return render(request, 'operations/contributions/view_employee_contributions.html', context)
