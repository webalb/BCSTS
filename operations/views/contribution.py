from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime, timedelta
import calendar
from operations.models import ContributionRecord, ContributionSetting, ContributionSettingHistory, ContributionSettingPermissions
from django.db.models import Sum, Q
from operations.forms import ContributionSettingForm, ContributionSettingAdminForm, ContributionSettingPermissionForm
from django.utils.timezone import now
from accounts.models import CustomUser
from withdrawal.models import EmployeeAccountDetails, WithdrawalCharge, EmployeeSavings, WithdrawalTransaction
from django.utils import timezone

from withdrawal.models import WithdrawalRequest

# Admin check function
def is_admin(user):
    return user.groups.filter(name="admin").exists()

def is_employee(user):
    return user.groups.filter(name="Employee").exists()

def calculate_contribution_durations(employee):
    """
    Get the durations for which an employee used each contribution setting before changing it.
    Also calculates the total amount paid during each contribution period.
    """
    history = ContributionSettingHistory.objects.filter(
        contribution_setting__employee=employee
    ).order_by('changed_at')

    durations = []
    previous_entry = None

    for entry in history:
        if previous_entry:
            duration = entry.changed_at - previous_entry.changed_at
            
            # Calculate total paid within this period
            total_paid = ContributionRecord.objects.filter(
                employee=employee,
                created_at__range=[previous_entry.changed_at, entry.changed_at],
                status="paid"
            ).aggregate(total=Sum("amount"))["total"] or 0

            durations.append({
                "amount": previous_entry.amount,
                "start_date": previous_entry.changed_at,
                "end_date": entry.changed_at,
                "duration_days": duration.days,
                "duration_months": round(duration.days / 30, 2),
                "total_paid": total_paid
            })
        previous_entry = entry

    # If the latest setting is still in use, calculate duration till today
    if previous_entry:
        duration = now() - previous_entry.changed_at
        
        # Calculate total paid till today
        total_paid = ContributionRecord.objects.filter(
            employee=employee,
            created_at__gte=previous_entry.changed_at,
            status="paid"
        ).aggregate(total=Sum("amount"))["total"] or 0

        durations.append({
            "amount": previous_entry.amount,
            "start_date": previous_entry.changed_at,
            "end_date": "Still in use",
            "duration_days": duration.days,
            "duration_months": round(duration.days / 30, 2),
            "total_paid": total_paid
        })

    return durations

@login_required
@user_passes_test(is_employee)
def dashboard(request):
    employee = request.user
    contribution_setting = ContributionSetting.objects.filter(employee=employee).first()
    contribution_history = ContributionSettingHistory.objects.filter(contribution_setting=contribution_setting).order_by('-changed_at')
    contribution_records = ContributionRecord.objects.filter(employee=employee).order_by('-year', '-month')
    account_details = EmployeeAccountDetails.objects.filter(employee=employee).first()
    
    # Calculate contribution durations
    contribution_durations = calculate_contribution_durations(employee)

    try:
        withdrawal_request = WithdrawalRequest.objects.filter(employee=employee).latest('created_at')
        savings = EmployeeSavings.objects.get(employee=employee).total_to_withdraw
        
        if withdrawal_request.withdrawal_type == 'complete':
            charge_model = WithdrawalCharge.objects.filter(
                withdrawal_type=withdrawal_request.withdrawal_type, 
                reason=withdrawal_request.reason
            ).first()
        else:
            charge_model = WithdrawalCharge.objects.filter(
                withdrawal_type=withdrawal_request.withdrawal_type
            ).first()

        # Fetch the latest transaction for the withdrawal request
        transaction = WithdrawalTransaction.objects.filter(request=withdrawal_request).order_by('-transaction_date').first()

    except WithdrawalRequest.DoesNotExist:
        withdrawal_request = None
        savings = None
        charge_model = None
        transaction = None

    charges = (charge_model.charge_percentage / 100) * withdrawal_request.amount if charge_model else 0
    total_debit_amount = withdrawal_request.amount + charges if withdrawal_request else 0

    # Fetch permission for contribution setting update
    permissions = ContributionSettingPermissions.objects.filter(employee=employee).first()

    context = {
        'employee': employee,
        'contribution_setting': contribution_setting,
        'contribution_history': contribution_history,
        'contribution_records': contribution_records,
        'contribution_durations': contribution_durations,
        'permissions': permissions,
        'account_details': account_details,
        'withdrawal_request': withdrawal_request,
        'savings': savings,
        'charges': charges,
        'total_debit_amount': total_debit_amount,
        'transaction': transaction,  # Include transaction details
    }

    return render(request, 'operations/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def record_all_contributions(request):
    """Admin triggers all employee contribution deductions for the current month."""
    today = timezone.now().date()
    
    # Ensure today is 25th or later
    if today.day < 7:
        messages.warning(request, "You can only record contributions on or after the 25th of the month.")
        return redirect('admin_dashboard')

    # Check if contributions for the current month already exist
    current_month = today.month
    current_year = today.year
    contributions_exist = ContributionRecord.objects.filter(
        year=current_year, 
        month=current_month
    ).exists()

    if contributions_exist:
        messages.warning(request, "All contributions for this month have already been recorded.")
        return redirect('admin_dashboard')

    # If conditions are met, record contributions
    records_created = ContributionRecord.bulk_record_contributions()
    
    if records_created > 0:
        messages.success(request, f"Successfully recorded {records_created} contributions for this month.")
    else:
        messages.warning(request, "No employee contributions were recorded.")

    return redirect('admin_dashboard')

@login_required
def contribution_history(request):
    """Fetches the logged-in employee's contribution history."""
    contributions = ContributionRecord.objects.filter(employee=request.user).order_by('-year', '-month')
    return render(request, 'operations/contributions/history.html', {'contributions': contributions})


@login_required
def view_contributions(request, employee_id):
    employee = get_object_or_404(CustomUser, id=employee_id)
    contributions = ContributionRecord.objects.filter(employee=employee).order_by('-year', '-month')
    
    total_contributed = contributions.aggregate(total=Sum("amount"))["total"] or 0
    
    context = {
        'employee': employee,
        'contributions': contributions,
        'total_contributed': total_contributed,
    }
    
    return render(request, 'operations/contributions/view_contributions.html', context)

@login_required
def download_contribution_history(request):
    """Generates and downloads a PDF of the user's contribution history."""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Contribution_History_{request.user.nitda_id}.pdf"'
    
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Title
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, height - 50, f"{request.user.nitda_id}'s Contribution History")
    
    # Date generated
    p.setFont("Helvetica", 10)
    p.drawString(200, height - 70, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Table headers
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 100, "Month")
    p.drawString(150, height - 100, "Year")
    p.drawString(250, height - 100, "Amount")
    p.drawString(350, height - 100, "Status")
    
    # Fetch contributions
    contributions = ContributionRecord.objects.filter(employee=request.user).order_by('-year', '-month')
    y_position = height - 120
    p.setFont("Helvetica", 11)

    for contribution in contributions:
        p.drawString(50, y_position, calendar.month_name[contribution.month])
        p.drawString(150, y_position, str(contribution.year))
        p.drawString(250, y_position, f"₦{contribution.amount}")
        p.drawString(350, y_position, "Paid" if contribution.status == "paid" else "Pending")
        y_position -= 20  # Move to the next row

        if y_position < 50:
            p.showPage()
            y_position = height - 50

    p.showPage()
    p.save()
    return response

@login_required
def contribution_setting_view(request):
    """Displays and updates the user's contribution settings."""
    contribution_setting, _ = ContributionSetting.objects.get_or_create(employee=request.user)
    permissions = ContributionSettingPermissions.objects.filter(employee=request.user).first()
    
    if permissions and permissions.can_update:
        if request.method == "POST":
            form = ContributionSettingForm(request.POST, instance=contribution_setting)
            if form.is_valid():
                form.save()
                messages.success(request, "Contribution setting updated successfully.")
                return redirect("contribution_setting")
        else:
            form = ContributionSettingForm(instance=contribution_setting)
    else:
        form = None
        messages.info(request, "You are not allowed to update your contribution settings.")
        
    return render(request, "operations/contributions/contribution_setting.html", {"form": form})

@login_required
def manage_contribution_setting(request):
    """Creates or updates ContributionSetting."""
    
    # Check if the employee already has a contribution setting
    contribution_setting = ContributionSetting.objects.filter(employee=request.user).first()

    # Check for the permissions if the employee can update the contribution setting
    permissions = ContributionSettingPermissions.objects.filter(employee=request.user).first()

    if request.method == 'POST':
        # If the employee doesn't have a contribution setting, we create it
        if not contribution_setting:
            form = ContributionSettingForm(request.POST)
            if form.is_valid():
                # Create a new contribution setting for the employee
                contribution_setting = form.save(commit=False)
                contribution_setting.employee = request.user
                contribution_setting.save()
                messages.success(request, "Contribution setting created successfully.")
                return redirect('dashboard')
        # If contribution setting exists and employee has permission to update
        elif permissions and permissions.can_update:
            form = ContributionSettingForm(request.POST, instance=contribution_setting)
            if form.is_valid():
                form.save()
                messages.success(request, "Contribution setting updated successfully.")
                return redirect('dashboard')
            else:
                messages.error(request, "There was an error updating your contribution setting.")
        else:
            messages.warning(request, "You are not allowed to update your contribution setting.")
            return redirect('dashboard')
    else:
        if contribution_setting:
            # If contribution setting exists, check if employee can update it
            if permissions and permissions.can_update:
                form = ContributionSettingForm(instance=contribution_setting)
            else:
                form = None
                messages.info(request, "Your contribution setting is already set. You cannot update it.")
        else:
            form = ContributionSettingForm()
            messages.info(request, "Please set your contribution setting for the first time.")

    return render(request, 'operations/contributions/contribution_setting.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def delete_contribution_setting(request):
    """Deletes the user's ContributionSetting."""
    contribution_setting = getattr(request.user, 'contribution_setting', None)
    if request.method == 'POST' and contribution_setting:
        contribution_setting.delete()
        messages.success(request, "Contribution setting deleted successfully.")
        return redirect('dashboard')
    return render(request, 'operations/contributions/delete_contribution_setting.html', {'contribution_setting': contribution_setting})


@login_required
@user_passes_test(is_admin)
def manage_employee_permissions(request, employee_id):
    """Admin manages employee permission to update contribution settings."""
    employee = get_object_or_404(CustomUser, id=employee_id)
    permissions, created = ContributionSettingPermissions.objects.get_or_create(employee=employee)
    
    if request.method == "POST":
        form = ContributionSettingPermissionForm(request.POST, instance=permissions)
        if form.is_valid():
            form.save()
            messages.success(request, f"Permissions updated for {employee.username}.")
            return redirect('admin_dashboard')
    else:
        form = ContributionSettingPermissionForm(instance=permissions)
        
    return render(request, 'operations/contributions/manage_permissions.html', {'form': form, 'employee': employee})


@login_required
@user_passes_test(is_admin)
def manage_employee_contributions(request):
    """Admin view to list all employees' contribution settings and those without settings."""
    
    all_employees = CustomUser.objects.exclude(Q(is_superuser=True) | Q(groups__name="Admin")).distinct()

    # Get employees with contribution settings
    contribution_settings = ContributionSetting.objects.select_related('employee')

    # Identify employees without contribution settings
    employees_without_settings = all_employees.exclude(id__in=contribution_settings.values_list('employee_id', flat=True))

    print(all_employees)
    return render(request, 'operations/contributions/employee_contribution_setting.html', {
        'contribution_settings': contribution_settings,
        'employees_without_settings': employees_without_settings
    })


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
            contribution_setting.employee = employee
            contribution_setting.save()
            messages.success(request, "Contribution setting created successfully.")
            return redirect('manage_employee_contributions')
    else:
        form = ContributionSettingAdminForm(initial={'employee': employee})

    return render(request, 'operations/contributions/contribution_setting.html', {'form': form})

# Admin view to update an existing contribution setting
@login_required
@user_passes_test(is_admin)
def update_contribution_setting(request, pk):
    """Updates an existing contribution setting for an employee."""
    contribution_setting = get_object_or_404(ContributionSetting, pk=pk)
    if request.method == 'POST':
        form = ContributionSettingAdminForm(request.POST, instance=contribution_setting)
        if form.is_valid():
            form.save()
            messages.success(request, "Contribution setting updated successfully.")
            return redirect('manage_employee_contributions')
    else:
        form = ContributionSettingAdminForm(instance=contribution_setting)
    return render(request, 'operations/contributions/contribution_setting.html', {'form': form})

# Admin view to delete a contribution setting
@login_required
@user_passes_test(is_admin)
def delete_contribution_setting(request, pk):
    """Deletes an employee's contribution setting."""
    contribution_setting = get_object_or_404(ContributionSetting, pk=pk)
    contribution_setting.delete()
    messages.success(request, "Contribution setting deleted successfully.")
    return redirect('manage_employee_contributions')







from django.db.models import Max, Count, OuterRef, Subquery, Exists
from django.utils.timezone import now


from django.db.models import OuterRef, Subquery, Exists

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

    context = {
        "contributions": contributions,
        "missing_contributions": missing_contributions,
        "selected_month": selected_month,
        "selected_year": selected_year,
        "available_months": available_months,
        "available_years": available_years,
    }
    
    return render(request, "operations/contributions/manage_contributions.html", context)

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
            amount=employee.contribution_setting.amount,
            month=selected_month,
            year=selected_year,
            status='pending'
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
            amount=employee.contribution_setting.amount,
            month=selected_month,
            year=selected_year,
            status='pending'
        )
        records_created += 1

    if records_created > 0:
        messages.success(request, f"Successfully recorded {records_created} contributions.")
    else:
        messages.warning(request, "No new contributions were recorded.")

    return redirect('manage_contributions')



from django.http import Http404


@login_required
@user_passes_test(is_admin)
def admin_contribution_history(request, employee_id):
    
    records = ContributionSettingHistory.objects.filter(
            contribution_setting__employee__id=employee_id
        )
    
    return render(request, 'operations/contributions/contribution_history.html', {'records': records})

@login_required
@user_passes_test(is_admin)
def delete_contribution_history(request, record_id):
    """ Delete a specific contribution history record. """
    
    try:
        # Fetch the record
        record = ContributionSettingHistory.objects.get(id=record_id)
        employee_id = record.employee.id
        record.delete()
        messages.success(request, 'Contribution history record deleted successfully.')
    except ContributionSettingHistory.DoesNotExist:
        raise Http404("Contribution history record does not exist.")
    
    return redirect('admin_contribution_history', employee_id=employee_id)  # Redirect back to the history page
