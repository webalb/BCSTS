from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from operations.models import ContributionRecord, ContributionSetting
from django.contrib.auth import get_user_model
from django.db.models import Sum, Q
from accounts.models import CustomUser as User
from withdrawal.models import WithdrawalTransaction
from django.contrib.auth.models import Group
import json

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
    
    from django.utils import timezone

    transactions = WithdrawalTransaction.objects.all().order_by('-transaction_date')
    total_withdrawn = transactions.aggregate(Sum('final_amount'))['final_amount__sum'] or 0


    today = timezone.now().date()
    current_month = today.month
    current_year = today.year

    # Check if contributions for the current month already exist
    contributions_exist = ContributionRecord.objects.filter(
        year=current_year, 
        month=current_month
    ).exists()

    contributions = ContributionRecord.objects.all()
    total_amount_raised = contributions.aggregate(Sum('amount'))['amount__sum'] or 0

    employee_contributions = []
    labels = []  # For chart labels (Employee names)
    data = []    # For chart data (Total contributions)

    for employee in employees:
        total_contributed = contributions.filter(employee=employee).aggregate(Sum('amount'))['amount__sum'] or 0
        employee_contributions.append({
            'employee': employee,
            'total_contributed': total_contributed,
            'contributions': contributions.filter(employee=employee)
        })

        if total_contributed > 0:  # Only show employees with contributions
            labels.append(employee.get_full_name())  # Store only the employee name
            data.append(float(total_contributed))    # Convert Decimal to float

    context = {
        'employees': employees,
        'total_employees': total_employees,
        'total_amount_raised': total_amount_raised,
        "contributions_exist": contributions_exist,
        'employee_contributions': employee_contributions,
        'chart_labels': json.dumps(labels),  # Convert list to JSON string
        'chart_data': json.dumps(data),      # Convert list to JSON string
        'today': today,
        'total_withdrawn': total_withdrawn,
        'total_remained': total_amount_raised - total_withdrawn,
    }
    return render(request, 'operations/admin_dashboard.html', context)
