from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.db.models import Sum

from operations.models import Expense
from operations.forms import ExpenseForm
from operations.utils import get_system_financial_summary
from accounts.models import CustomUser as User
from notification.services import NotificationService
from notification.models import Notification

# Admin check function
def is_admin(user):
    return user.groups.filter(name="Admin").exists()

@login_required
@user_passes_test(is_admin)
def manage_expenses(request):
    """View to list, add, and delete expenses."""
    
    expenses = Expense.objects.all().order_by("-created_at")  # Get all expenses sorted by date
    finance = get_system_financial_summary()['total_system_investment_balance']
    total_expense = finance["total_expenses"]
    investment_balance = finance['total_system_investment_balance']
    if request.method == "POST":
        # Replace currency comma with empty string for amount
        if 'amount' in request.POST:
            request.POST = request.POST.copy()  # Make POST mutable
            request.POST['amount'] = request.POST['amount'].replace(',', '')
        form = ExpenseForm(request.POST)
        if form.is_valid():
            # Check if expense with same details already exists
            existing_expense = Expense.objects.filter(
                amount=form.cleaned_data['amount'],
                description=form.cleaned_data['description'],
            ).first()
            
            if existing_expense:
                messages.warning(request, "An identical expense already exists!")
                return redirect("manage_expenses")
            form.save()
            # Send notification to all admin users
            admin_users = User.objects.filter(groups__name='Admin')
            for admin in admin_users:
                NotificationService.send_notification(
                    admin,
                    heading="New Expense Added",
                    message=f"A new expense of {form.cleaned_data['amount']} has been added for {form.cleaned_data['description']}",
                    link=reverse("manage_expenses"),
                    notification_type=Notification.NotificationType.IN_APP
                )
            messages.success(request, "Expense added successfully!")
            return redirect("manage_expenses")
    else:
        form = ExpenseForm()

    context = {
        "expenses": expenses,
        "investment_balance": investment_balance,
        "total_expense": total_expense,
        "form": form,
    }
    return render(request, "operations/expenses/manage_expenses.html", context)

@require_POST
@login_required
@user_passes_test(is_admin)
def delete_expense(request, expense_id):
    """View to delete an expense via AJAX."""
    expense = get_object_or_404(Expense, id=expense_id)
    expense.delete()
    # Send notification to all admin users about expense deletion
    admin_users = User.objects.filter(groups__name='Admin')
    for admin in admin_users:
        NotificationService.send_notification(
            admin,
            heading="Expense Deleted",
            message=f"An expense of {expense.amount} for {expense.description} has been deleted",
            link=reverse("manage_expenses"),
            notification_type=Notification.NotificationType.IN_APP
        )
    messages.success(request, "Expense deleted successfully!")
    return redirect("manage_expenses")
