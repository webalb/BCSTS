import re
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.conf import settings

from withdrawal.views import is_admin
from .models import CustomUser
from .forms import EmployeeUpdateForm
from operations.models import ContributionSetting
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import Group  # Import Group
from operations.utils import get_employee_financial_summary  # Utility function
from notification.models import Notification
from notification.services import NotificationService
from django.contrib.auth import logout
from django.contrib.sessions.models import Session


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")



@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()

            # Logout user from all devices by deleting all sessions linked to the user
            sessions = Session.objects.filter(expire_date__gte=user.last_login)
            for session in sessions:
                data = session.get_decoded()
                if data.get('_auth_user_id') == str(user.id):
                    session.delete()
            
            # Log out the current session
            logout(request)
            
            messages.success(request, 'Your password has been successfully updated! Please log in again.')
            return redirect('redirect_user')  # Update this with your actual login URL
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/settings.html', {'password_form': form})

from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.urls import resolve, reverse
import user_agents # type: ignore

def my_login_view(request):
    next_url = request.GET.get('next')  # Get the 'next' URL from the query parameters
    redirect_user_url = reverse('redirect_user')  # Default redirection URL

    if request.method == 'POST':
        form = AuthenticationForm(request, request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            

            # Extract User Agent Data
            user_agent_str = request.META.get('HTTP_USER_AGENT', '')
            user_agent = user_agents.parse(user_agent_str)
            browser = user_agent.browser.family or "Unknown Browser"
            os_family = user_agent.os.family or "Unknown OS"

            # Send in-app login notification
            message = f"You have a new login from {browser} browser running on {os_family} OS."
            NotificationService.send_notification(
                user,
                "New Login Alert",
                message,
                notification_type=Notification.NotificationType.IN_APP
            )

            # Redirect User
            if next_url:
                try:
                    resolve(next_url)  # Check if the next URL is valid
                    return redirect(next_url)
                except Exception:
                    messages.warning(request, "The 'next' URL is invalid. Redirecting to default.")
                    return redirect(redirect_user_url)
            else:
                return redirect(redirect_user_url)

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error: {error}")

    else:
        form = AuthenticationForm(request)

    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})  # Pass next_url to the template



# ============================
# User CRUD for admin
# ===========================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from .models import CustomUser
from .forms import EmployeeForm

@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name="Admin").exists())
def employee_list(request):
    """View for listing employees (excluding superusers and admins)."""
    employees = CustomUser.objects.exclude(Q(is_superuser=True) | Q(groups__name="Admin")).distinct()
    return render(request, 'operations/employee/employee_list.html', {'employees': employees})

@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name="Admin").exists())
def create_employee(request):
    """View for creating a new employee."""
    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            contribution_amount = form.cleaned_data.get("contribution_amount")

            # Validate contribution amount (must be at least 1,000)
            if contribution_amount is None or contribution_amount < 1000:
                form.add_error("contribution_amount", "Contribution amount must be at least 1,000.")
                return render(request, "operations/employee/employee_form.html", {"form": form, "action": "Create"})

            employee = form.save(commit=False)
            employee.save()

            # Assign employee to the "Employee" group
            try:
                employee_group = Group.objects.get(name="Employee")
                employee.groups.add(employee_group)
            except Group.DoesNotExist:
                messages.error(request, "The 'Employee' group does not exist. Please contact the administrator.")
                employee.delete()  # Prevent incomplete registration
                return redirect("create_employee")

            # Create contribution setting for the employee
            ContributionSetting.objects.create(employee=employee, amount=contribution_amount)

            NotificationService.send_notification(
                employee,
                "Welcome to Benevolence Cooperative!",
                "You have been successfully registered as a member of BCS, with initial monthly contribution amount: ₦{contribution_amount}",
                notification_type=Notification.NotificationType.IN_APP
            )
            messages.success(request, f"Contributor created successfully with an initial contribution of ₦{contribution_amount:,.2f}")
            return redirect("employee_list")

    else:
        form = EmployeeForm()

    return render(request, "operations/employee/employee_form.html", {"form": form, "action": "Create"})

from django.forms.models import model_to_dict

@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name="Admin").exists())
def update_employee(request, employee_id):
    """View for updating an employee."""
    employee = get_object_or_404(CustomUser, id=employee_id)
    
    # Capture original data before updating
    original_data = model_to_dict(employee)

    form = EmployeeUpdateForm(request.POST or None, request.FILES or None, instance=employee)
    
    if form.is_valid():
        form.save()

        # Identify changed fields
        updated_fields = []
        for field, new_value in form.cleaned_data.items():
            original_value = original_data.get(field)
            if str(original_value) != str(new_value):  # Convert to string for comparison
                updated_fields.append(f"<strong>{field.replace('_', ' ').title()}</strong>: {original_value} ➝ {new_value}")

        # Send notification if fields were changed
        if updated_fields:
            changes = "<br>".join(updated_fields)  
            notification_message = f"""
            <p>Your profile details have been updated by the admin. Below are the changes:</p>

            {changes}

            <p>If you did not authorize this update, please contact the management immediately.</p>
            """
            dashboard_link = reverse("employee_specific_detail", kwargs={"employee_id": employee.id})  # type: ignore # Adjust if needed
            NotificationService.send_notification(
                employee,
                "Profile Update Notification",
                notification_message,
                dashboard_link,
                notification_type=Notification.NotificationType.IN_APP
            )

        messages.success(request, "Employee updated successfully!")
        return redirect('employee_list')

    return render(request, 'operations/employee/employee_form.html', {'form': form, 'action': 'Update'})

@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name="Admin").exists())
def delete_employee(request, employee_id):
    """View for deleting an employee."""
    employee = get_object_or_404(CustomUser, id=employee_id)
    if request.method == "POST":
        employee.delete()
        messages.success(request, "Employee deleted successfully!")
        return redirect('employee_list')
    return render(request, 'operations/employee/employee_confirm_delete.html', {'employee': employee})

@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name="Admin").exists())
def employee_detail(request, employee_id):
    """Fetches detailed financial information for a specific employee."""
    employee = get_object_or_404(CustomUser, id=employee_id)

    # Get financial summary from utility function
    financial_summary = get_employee_financial_summary(employee)

    context = {
        'employee': employee,
        'total_contributions': financial_summary["total_contributions"],
        'savings_balance': financial_summary["savings_balance"],
        'investment_balance': financial_summary["investment_balance"],
        'total_remained_balance': financial_summary["total_remained_balance"],
        'total_withdrawn': financial_summary["total_withdrawn"],
        'took_credits': financial_summary["took_credits"],
        'repaid_credits': financial_summary["repaid_credits"],
        "repaid_percentage": financial_summary["repaid_percentage"],
    }

    return render(request, 'operations/employee/employee_detail.html', context)

@login_required
@user_passes_test(lambda u: u.groups.filter(name="Employee").exists())
def employee_specific_detail(request, employee_id):
    """Fetches detailed financial information for a specific employee."""
    employee = get_object_or_404(CustomUser, id=employee_id)

    # Get financial summary from utility function
    financial_summary = get_employee_financial_summary(employee)


    context = {
        'employee': employee,
        'total_contributions': financial_summary["total_contributions"],
        'savings_balance': financial_summary["savings_balance"],
        'investment_balance': financial_summary["investment_balance"],
        'total_remained_balance': financial_summary["total_remained_balance"],
        'total_withdrawn': financial_summary["total_withdrawn"],
        'took_credits': financial_summary["took_credits"],
        'repaid_credits': financial_summary["repaid_credits"],
        "repaid_percentage": financial_summary["repaid_percentage"],
    }

    return render(request, 'operations/employee/employee_specific_detail.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name="Admin").exists())
def toggle_employee_active(request, employee_id):
    employee = get_object_or_404(CustomUser, id=employee_id)
    employee.is_active = not employee.is_active
    employee.save()
    return redirect('employee_list')  # Redirect to your employee list view


from accounts.models import CustomUser as BCSMember
from operations.models import ContributionRecord as Contribution
from withdrawal.models import Withdrawals
from credit.models import Credit  # Import your models
import datetime
from operations.utils import get_employee_financial_summary

def view_mcr(request, nitda_id):
    """Displays the member timeline in the browser."""

    member = get_object_or_404(BCSMember, nitda_id=nitda_id)
    contributions = Contribution.objects.filter(employee=member).order_by('-created_at')
    withdrawals = Withdrawals.objects.filter(employee=member).order_by('-request_date')
    credits = Credit.objects.filter(applicant=member).order_by('-date_applied')
    financial_summary = get_employee_financial_summary(member)
    context = {
        'member': member,
        'contributions': contributions,
        'withdrawals': withdrawals,
        'compiled_date': datetime.datetime.now(),
        'compiled_time': datetime.datetime.now().strftime("%H:%M:%S"), #add time to context.
        'credits': credits,
        "financial_summary": financial_summary,
    }

    return render(request, 'documents/bcs-mcr.html', context)

from django.shortcuts import render, redirect
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from withdrawal.forms import  EmployeeAccountForm
from operations.forms import ContributionSettingForm

@login_required
def account_settings(request):
    """Handles user settings."""
    password_form = PasswordChangeForm(request.user, prefix='password')
    bank_form = EmployeeAccountForm(prefix='bank')
    contribution_form = ContributionSettingForm(prefix='contribution')

    return render(request, 'accounts/settings.html', {
        'password_form': password_form,
        'bank_form': bank_form,
        'contribution_form': contribution_form,
        'API_KEY': settings.PAYSTACK_SCRET_KEY,
    })


import pandas as pd
from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.contrib import messages
from django.db import IntegrityError
from accounts.models import CustomUser
from django.utils.crypto import get_random_string

@login_required
@user_passes_test(is_admin)
def bulk_upload_users(request):
    if request.method == 'POST' and request.FILES.get('file'):

        if request.session and 'users_preview' in request.session:
            del request.session['users_preview']

        file = request.FILES['file']
        fs = FileSystemStorage()
        filename = fs.save(file.name, file)
        file_url = fs.path(filename)

        try:
            df = pd.read_excel(file_url)

            # Validate columns
            required_columns = {'Username', 'Email', 'Phone', 'Name', 'NITDAID'}
            if not required_columns.issubset(df.columns):
                return JsonResponse({"error": "Invalid file format. Required columns: Username, Email, Phone, Name, NITDAID"}, status=400)

            preview_data = df.to_dict(orient='records')
            request.session['users_preview'] = preview_data  # Store data in session for final submission
            return JsonResponse({"success": True, "preview_data": preview_data})  # Send preview JSON
        
        except Exception as e:
            return JsonResponse({"error": f"Error processing file: {str(e)}"}, status=500)

    return render(request, 'accounts/bulk_create_users.html')

@login_required
@user_passes_test(is_admin)
def confirm_bulk_user_upload(request):
    preview_data = request.session.get('users_preview', [])
    if not preview_data:
        return JsonResponse({"error": "No data to process."}, status=400)

    success_count, duplicate_count = 0, 0

    for row in preview_data:
        username = row.get('Username')
        email = row.get('Email')
        phone_number = row.get('Phone')
        full_name = row.get('Name')
        nitda_id = row.get('NITDAID')

        if CustomUser.objects.filter(username=username).exists() or \
           CustomUser.objects.filter(email=email).exists() or \
           CustomUser.objects.filter(phone_number=phone_number).exists() or \
           CustomUser.objects.filter(nitda_id=nitda_id).exists():
            duplicate_count += 1
            continue

        try:
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                phone_number=phone_number,
                full_name=full_name,
                nitda_id=nitda_id,
                password="default-bcs"  # Generate a random password
            )
            success_count += 1
        except IntegrityError:
            duplicate_count += 1

    del request.session['users_preview']
    return JsonResponse({"success": True, "uploaded": success_count, "duplicates": duplicate_count})

from django.http import JsonResponse
from django.contrib import messages
from django.utils.timezone import make_aware
from datetime import datetime
from operations.models import ContributionRecord
from accounts.models import CustomUser
from django.db import models
from django.db.models import Min

def update_employee_date_joined(request):
    # Step 1: Get the earliest year for each employee
    employee_earliest_years = (
        ContributionRecord.objects.values("employee")
        .annotate(first_year=Min("year"))  # Find the earliest year per employee
    )

    for record in employee_earliest_years:
        employee_id = record["employee"]
        first_year = record["first_year"]

        # Step 2: Find the earliest month in that specific year
        first_month = (
            ContributionRecord.objects.filter(employee=employee_id, year=first_year)
            .aggregate(first_month=Min("month"))["first_month"]
        )

        if first_month:
            # Construct the first day of that month
            first_contribution_date = datetime(first_year, first_month, 1)
            aware_date = make_aware(first_contribution_date)  # Ensure timezone-aware datetime

            # Update the employee's date_joined field
            CustomUser.objects.filter(id=employee_id).update(date_joined=aware_date)

    messages.success(request, "Employees' date_joined has been updated successfully.")
    return JsonResponse({"message": "Employee join dates updated successfully!"})

from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
import json

User = get_user_model()

@csrf_exempt
def admin_reset_member_password(request, employee_id):
    member = User.objects.get(id=employee_id)

    if request.method == "POST":
        new_password = request.POST.get("new_password")

        try:
            member.set_password(new_password)
            member.save()
            messages.success(request, f"Password changed successfully for {member.full_name}")
            return redirect("employee_detail", employee_id=employee_id)
        except User.DoesNotExist:
            messages.error(request, f"Something went wrong!")
            return redirect("employee_detail", employee_id=employee_id)
    
    return redirect("employee_detail", employee_id=employee_id)
import os
from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import render
from django.core.management import call_command

def generate_and_download_backup(request):
    """
    Generates a database backup and provides it as a downloadable file.
    """
    if request.method == 'POST':
        try:
            # Generate the database backup
            call_command('dbbackup', interactive=False)

            # Find the latest backup file
            backup_dir = settings.DBBACKUP_STORAGE_OPTIONS.get('location', settings.MEDIA_ROOT) #defaults to media root if not specified.
            backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.dump')] #change to .zip or whatever your backup extension is.

            if not backup_files:
                return HttpResponse("No backup files found.", status=404)

            latest_backup = max(backup_files, key=lambda f: os.path.getctime(os.path.join(backup_dir, f)))
            backup_path = os.path.join(backup_dir, latest_backup)

            # Provide the file as a download
            response = FileResponse(open(backup_path, 'rb'), as_attachment=True, filename=latest_backup)
            return response

        except Exception as e:
            # Handle any errors that occur during backup generation or download
            return HttpResponse(f"An error occurred: {e}", status=500)

    # Render a simple HTML page with a button
    return redirect('settings')

