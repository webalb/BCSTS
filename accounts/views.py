from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from .models import CustomUser
from .forms import RegistrationForm, EmployeeUpdateForm
from operations.models import ContributionSetting
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import Group  # Import Group
from operations.utils import get_employee_financial_summary  # Utility function
from notification.models import Notification
from notification.services import NotificationService

# ... other imports
# for user registration
def register(request):
    """Handles user registration."""

    if request.method == "POST":
        form = RegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            contribution_amount = form.cleaned_data.get("contribution_amount")

            # Ensure contribution is at least 1000
            if contribution_amount is None or contribution_amount < 1000:
                form.add_error("contribution_amount", "Contribution amount must be at least 1,000.")
                return render(request, "accounts/register.html", {"form": form})

            user = form.save(commit=False)
            user.is_active = True 
            user.save()

            # Assign default role (employee group)
            try:
                employee_group = Group.objects.get(name="Employee")
                user.groups.add(employee_group)
            except Group.DoesNotExist:
                messages.error(request, "The 'Employee' group does not exist. Please contact the administrator.")
                user.delete()  # Prevent incomplete registration
                return redirect("register")

            # Create contribution setting
            ContributionSetting.objects.create(employee=user, amount=contribution_amount)

            # # Send email verification
            # current_site = get_current_site(request)
            # subject = "Verify your Email - Benevolence Cooperative"
            # message = render_to_string(
            #     "accounts/email_verification.html",
            #     {
            #         "user": user,
            #         "domain": current_site.domain,
            #         "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            #         "token": user.verification_token,
            #     },
            # )
            # send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
            return redirect("login")

            # return HttpResponse("Check your email for a verification link.")
    else:
        form = RegistrationForm()

    return render(request, "accounts/register.html", {"form": form, 'action': "Create"})



def activate_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid, verification_token=token)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        return HttpResponse("Invalid verification link.")

    # Activate the user
    user.is_active = True
    user.is_email_verified = True
    user.verification_token = None
    user.save()

    # Send in-app notification
    link = reverse("dashboard")
    NotificationService.send_notification(
        user,
        "Welcome to BCS",
        "Congratulations! Your account has been successfully activated. Explore BCS and enjoy the benefits.",
        link,
        notification_type=Notification.NotificationType.IN_APP
    )

    # Log the user in and redirect to dashboard
    login(request, user)
    return redirect("dashboard")

from django.contrib.auth import logout
from django.shortcuts import redirect

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

            update_session_auth_hash(request, user)  # Keep the user logged in
            messages.success(request, 'Your password has been successfully updated!')
            return redirect('dashboard')  # Redirect to the dashboard or another page
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})

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
            device = user_agent.device.brand or "Unknown Device"
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
                "You have been successfully registered as a member of BCS, with initial monthly contribution amount: ₦{contribution_amount:,.2f}",
                notification_type=Notification.NotificationType.IN_APP
            )
            # Send email notification with initial contribution amount
            subject = "Welcome to Benevolence Cooperative!"
            message = f"""
            Dear {employee.first_name},

            You have been successfully registered as a member of Benevolence Cooperative Society by the admin.

            Benevolence Cooperative operates under a Shariah-compliant financial model, ensuring ethical and interest-free financial transactions. We are committed to your financial growth and stability.

            Your initial monthly contribution amount has been set at **₦{contribution_amount:,.2f}**.

            Welcome aboard, and we look forward to growing together!

            Regards,  
            Benevolence Cooperative Management
            """
            # send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [employee.email])

            messages.success(request, f"Employee created successfully with an initial contribution of ₦{contribution_amount:,.2f}. An email notification has been sent!")
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
    employee = get_object_or_404(CustomUser, pk=employee_id)
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