from django.contrib.auth.decorators import login_required, user_passes_test
from accounts.models import CustomUser
from credit.models import Credit
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from credit.forms import CreditApplicationForm  # Assume you have a form for this model
from django.contrib import messages
from django.db import IntegrityError


def is_admin(user):
    return user.groups.filter(name="admin").exists()

def is_employee(user):
    return user.groups.filter(name="Employee").exists()


@login_required
@user_passes_test(is_employee)
def create_credit_application(request):
    if request.method == 'POST':
        form = CreditApplicationForm(request.POST)
        
        if form.is_valid():
            try:
                # Save the credit application
                credit_application = form.save(commit=False)
                credit_application.applicant = request.user  # Assuming the user is logged in
                credit_application.save()
                messages.success(request, "Credit application successfully submitted!")
                return redirect('credit_application_detail', credit_id=credit_application.id)
            except IntegrityError as e:
                messages.error(request, f"An error occurred: {e}")
                return redirect('create_credit_application')
        else:
            messages.error(request, "Form is invalid, please try again.")
    else:
        form = CreditApplicationForm()

    return render(request, 'credit/employee_credit_portal.html', {'form': form})

@login_required
@user_passes_test(is_employee)
def credit_application_detail(request, credit_id):
    credit_application = get_object_or_404(Credit, id=credit_id)
    return render(request, 'credit/credit_application_detail.html', {'credit_application': credit_application})
