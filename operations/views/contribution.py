from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.timezone import now
from django.db.models import Sum

from operations.models import ContributionRecord, ContributionSetting, ContributionSettingHistory, ContributionChangeRequest
from accounts.models import CustomUser
from withdrawal.models import EmployeeAccountDetails

from operations.utils import get_employee_financial_summary  # Utility function

def home(request):
    """Home view displaying a welcome message and navigation options."""

    return render(request, 'operations/home.html')

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
                "id": entry.id, # type: ignore
                "employee_email": entry.contribution_setting.employee.email,
                "amount": previous_entry.amount,
                "start_date": previous_entry.changed_at,
                "end_date": entry.changed_at,
                "duration_days": duration.days,
                "changed_by": entry.changed_by,
                "change_reason": entry.change_reason,
                "duration_months": round(duration.days / 30),
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
            "id": entry.id, # type: ignore
            "employee_email": entry.contribution_setting.employee.email, # type: ignore
            "amount": previous_entry.amount,
            "start_date": previous_entry.changed_at,
            "end_date": "Still in use",
            "duration_days": duration.days,
            "duration_months": round(duration.days / 30, 2),
            "total_paid": total_paid,
            "changed_by": entry.changed_by, # type: ignore
            "change_reason": entry.change_reason, # type: ignore

        })
    sorted_objects = sorted(durations, key=lambda item: item['start_date'], reverse=True)

    return sorted_objects

@login_required
@user_passes_test(is_employee)
def contribution_setting_history(request):
    employee = request.user
    # Calculate contribution durations
    contribution_durations = calculate_contribution_durations(employee)

    context = {
      'contribution_durations': contribution_durations ,
    }

    return render(request, 'operations/contributions/contribution_setting_history.html', context)



@login_required
@user_passes_test(is_employee)
def dashboard(request):
    """Employee dashboard displaying personal contributions, savings, and withdrawal status."""
    employee = request.user

    # Fetch contribution settings & history
    contribution_setting = ContributionSetting.objects.filter(employee=employee).first()
    contribution_history = ContributionSettingHistory.objects.filter(
        contribution_setting=contribution_setting
    ).order_by('-changed_at')

    # Fetch contribution records ordered by year and month
    contribution_records = ContributionRecord.objects.filter(employee=employee).order_by('-year', '-month')[:5]

    # Fetch employee account details
    account_details = EmployeeAccountDetails.objects.filter(employee=employee).first()

    # Calculate contribution durations using helper function
    contribution_durations = calculate_contribution_durations(employee)

    # Get financial summary using utils
    financial_summary = get_employee_financial_summary(employee)


    # Context for template rendering
    context = {
        'employee': employee,
        'contribution_setting': contribution_setting,
        'contribution_history': contribution_history,
        'contribution_records': contribution_records,
        'contribution_durations': contribution_durations,
        'account_details': account_details,
    
        # Financial summary from utils
        'total_contributions': financial_summary["total_contributions"],
        'savings_balance': financial_summary["savings_balance"],
        'investment_balance': financial_summary["investment_balance"],
        'total_remained_balance': financial_summary["total_remained_balance"],
        'total_withdrawn': financial_summary["total_withdrawn"],
    }

    return render(request, 'operations/dashboard.html', context)

# used
@login_required
@user_passes_test(is_employee)
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

# used
@login_required
@user_passes_test(is_employee)
def request_contribution_change(request):
    """ Employee requests to change their contribution amount. """

    if request.method == "POST":
        new_amount = request.POST.get("contribution-amount")

        # Ensure amount is valid
        try:
            new_amount = float(new_amount)
            if new_amount <= 15000:
                raise ValueError("Amount must not be less than N15,000.")
        except ValueError:
            messages.error(request, "Invalid amount entered.")
            return redirect("request_contribution_change")

        # Check if a request is already pending
        existing_request = ContributionChangeRequest.objects.filter(employee=request.user, status="pending").exists()
        if existing_request:
            messages.error(request, "You already have a pending request.")
            return redirect("settings")

        # Create the request
        ContributionChangeRequest.objects.create(
            employee=request.user,
            requested_amount=new_amount,
            status="pending"
        )

        messages.success(request, "Your request has been submitted for admin approval.")
        return redirect("dashboard")

    return render(request, 'accounts/settings.html')
