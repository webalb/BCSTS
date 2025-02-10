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
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import Group  # Import Group
# ... other imports

def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            # Assign default user role (using Groups)
            try:
                employee_group = Group.objects.get(name='employee')  # Get the 'employee' group
                user.groups.add(employee_group)  # Add the user to the group
                user.save()  # Save again to persist the group assignment

            except Group.DoesNotExist:
                messages.error(request, "The 'employee' group does not exist.")
                # Important: Handle the error appropriately
                # Option 1: Delete the user to prevent incomplete registration:
                user.delete()
                return redirect('register')  # Redirect to the registration page

                # Option 2:  Just log the error and let the registration proceed (less recommended):
                # import logging
                # logger = logging.getLogger(__name__)
                # logger.error("The 'employee' group does not exist.")


            # Send email confirmation (after role assignment)
            current_site = get_current_site(request)
            subject = "Verify your Email - Benevolence Cooperative"
            message = render_to_string("accounts/email_verification.html", {
                "user": user,
                "domain": current_site.domain,
                "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                "token": user.verification_token,
            })
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

            return HttpResponse("Check your email for a verification link.")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})

# ... (rest of your views)

# Email Verification View
def activate_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid, verification_token=token)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        return HttpResponse("Invalid verification link.")

    user.is_active = True
    user.is_email_verified = True
    user.verification_token = None
    user.save()

    login(request, user)
    return redirect("dashboard")  # Redirect to dashboard after verification
from django.contrib.auth import logout
from django.shortcuts import redirect

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

from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.urls import resolve, reverse

def my_login_view(request):
    next_url = request.GET.get('next')  # Get the 'next' URL from the query parameters
    redirect_user_url = reverse('redirect_user') # Replace 'redirect_user' with your actual URL name

    if request.method == 'POST':
        form = AuthenticationForm(request, request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Check if 'next' URL is valid and exists
            if next_url:
                try:
                    resolve(next_url)  # Check if the next URL is valid
                    return redirect(next_url)  # Redirect to 'next' URL
                except Exception:  # Handle invalid 'next' URL
                    messages.warning(request, "The 'next' URL is invalid. Redirecting to default.")
                    return redirect(redirect_user_url) # redirect to default
            else:
                return redirect(redirect_user_url)  # Redirect to default if 'next' is not provided
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    print(error)
                    messages.error(request, f"{field.capitalize()}: {error}")

    else:
        form = AuthenticationForm(request)

    return render(request, 'accounts/login.html', {'form': form, 'next': next_url}) # Pass next_url to the template



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
            employee = form.save(commit=False)
            
            employee.save()
            employee_group = Group.objects.get(name='Employee')  # Get the 'employee' group
            employee.groups.add(employee_group)
            messages.success(request, "Employee created successfully!")
            return redirect('employee_list')
    else:
        form = EmployeeForm()
    return render(request, 'operations/employee/employee_form.html', {'form': form, 'action': 'Create'})

@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name="Admin").exists())
def update_employee(request, employee_id):
    """View for updating an employee."""
    employee = get_object_or_404(CustomUser, id=employee_id)
    form = EmployeeUpdateForm(request.POST or None, request.FILES or None, instance=employee)
    if form.is_valid():
        form.save()
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
    employee = get_object_or_404(CustomUser, id=employee_id)
    return render(request, 'operations/employee/employee_detail.html', {'employee': employee})

@login_required
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name="Admin").exists())
def employee_detail(request, employee_id):
    employee = get_object_or_404(CustomUser, id=employee_id)
    return render(request, 'operations/employee/employee_detail.html', {'employee': employee})
