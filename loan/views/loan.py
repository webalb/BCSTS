from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from loan.models import Loan, MurabahaLoan, QardHasanLoan, Guarantor, RepaymentSetting
from loan.forms import LoanApplicationForm, GuarantorForm, RepaymentSettingForm, QardHasanLoanForm, MurabahaLoanForm
from django.core.mail import send_mail
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from accounts.models import CustomUser
from django.http import JsonResponse


def is_admin(user):
    return user.groups.filter(name="admin").exists()

def is_employee(user):
    return user.groups.filter(name="Employee").exists()

@login_required
@user_passes_test(is_employee)  # Only employees can apply
def loan_guidance(request):
    return render(request, 'loan/loan_guidance.html')

@login_required
@user_passes_test(is_employee)
def loan_application(request):
    if request.method == 'POST':
        form = LoanApplicationForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.applicant = request.user
            loan.save()
            messages.success(request, "Your loan application has been submitted!")
            return redirect('loan:loan_dashboard')  # Redirect to employee dashboard
    else:
        form = LoanApplicationForm()
    
    return render(request, 'loan/loan_application_form.html', {'form': form, 'title': 'Apply for Loan'})


@login_required
@user_passes_test(is_employee)
def loan_dashboard(request):
    # Fetch the loan where the current user is the applicant
    loan = Loan.objects.filter(applicant=request.user).first()

    # Fetch the loans where the current user is a guarantor
    loans_as_guarantor = Loan.objects.filter(guarantors__guarantor=request.user)
    comitee_to_review_loans = None
    if request.user.loan_committee_member.role:
        comitee_to_review_loans = Loan.objects.filter(status='Pending')


    # Check if the loan exists
    if loan:
        approved_guarantors = loan.guarantors.filter(status='Approved')

        approved_guarantor_count = approved_guarantors.count()
        remaining_guarantors = 2 - approved_guarantor_count  # A maximum of 2 approved guarantors needed

        # If there are rejected guarantors, allow the employee to add new ones
        rejected_guarantors = loan.guarantors.filter(status='Rejected')
        pending_guarantors = loan.guarantors.filter(status='Pending')
        allow_adding_guarantors = remaining_guarantors > 0

        # Check the loan status and set next action accordingly
        if not loan.details_completed:
            continue_url = 'loan:loan_details'
            next_action = "Complete Loan Details"

        elif not loan.repayment_setting:
            continue_url = 'loan:loan_repayment_setting'
            next_action = "Set Repayment Details"

        elif not loan.guarantors_added:
            continue_url = 'loan:loan_guarantors'
            next_action = "Add Guarantors"
        elif approved_guarantor_count >= 2:
            continue_url = None
            next_action = "Awaiting Committee Approval"
        else:
            continue_url = None
            next_action = "Awaiting Guarantor Approval"

        print(comitee_to_review_loans)
        return render(request, 'loan/loan_dashboard.html', {
            'loan': loan, 
            'continue_url': continue_url, 
            'next_action': next_action, 
            'loans_as_guarantor': loans_as_guarantor,
            'allow_adding_guarantors': allow_adding_guarantors,
            'rejected_guarantors': rejected_guarantors,
            'approved_guarantor_count': approved_guarantor_count,
            'remaining_guarantors': remaining_guarantors,
            'pending_guarantors': pending_guarantors,
            'comitee_to_review_loans': comitee_to_review_loans
        })
    
    return render(request, 'loan/loan_dashboard.html', {'loan': None, 'loans_as_guarantor': loans_as_guarantor})

from withdrawal.models import EmployeeSavings
@login_required
@user_passes_test(is_employee)
def loan_details(request):
    loan, created = Loan.objects.get_or_create(applicant=request.user)
    savings = EmployeeSavings.objects.get(employee=request.user)
    eligible_limit = savings.total_to_withdraw * 2  # Max loan eligibility

    if request.method == 'POST':
        if loan.loan_type == 'Murabaha':
            form = MurabahaLoanForm(request.POST, request.FILES)
        else:
            form = QardHasanLoanForm(request.POST)

        if form.is_valid():
            details = form.save(commit=False)
            details.loan = loan

            # Validate loan amount based on type
            if loan.loan_type == 'Murabaha' and details.asset_value > eligible_limit:
                messages.error(request, f"Asset value cannot exceed {eligible_limit} (twice your savings).")
            elif loan.loan_type == 'QardHasan' and details.total_loan_amount > eligible_limit:
                messages.error(request, f"Loan amount cannot exceed {eligible_limit} (twice your savings).")
            else:
                details.save()
                loan.details_completed = True
                loan.save()
                messages.success(request, "Loan details added successfully.")
                return redirect('loan:loan_dashboard')

    else:
        if loan.loan_type == 'Murabaha':
            form = MurabahaLoanForm()
        else:
            form = QardHasanLoanForm()

    return render(request, 'loan/details_form.html', {'form': form, 'eligible_limit': eligible_limit})

@login_required
@user_passes_test(is_employee)
def loan_guarantors(request):
    loan = get_object_or_404(Loan, applicant=request.user)

    if loan.guarantors_added:
        messages.info(request, "Guarantors have already been added.")
        return redirect('loan:loan_dashboard')

    if request.method == 'POST':
        form = GuarantorForm(request.POST, loan_type=loan.loan_type)
        if form.is_valid():
            guarantor_1_email = form.cleaned_data['guarantor_1']
            guarantor_2_email = form.cleaned_data.get('guarantor_2')

            try:
                guarantor_1 = CustomUser.objects.get(email=guarantor_1_email)

                if loan.loan_type == 'Murabaha' and guarantor_2_email:
                    guarantor_2 = CustomUser.objects.get(email=guarantor_2_email)

            except CustomUser.DoesNotExist:
                guarantor_2 = None

                if loan.loan_type == 'Murabaha' and guarantor_2_email:
                    guarantor_2 = None

            Guarantor.objects.create(loan=loan, guarantor=guarantor_1)

            if loan.loan_type == 'Murabaha' and guarantor_2:
                Guarantor.objects.create(loan=loan, guarantor=guarantor_2)

            # Send email notifications
            for email in [guarantor_1_email, guarantor_2_email] if guarantor_2_email else [guarantor_1_email]:
                send_mail(
                    'Guarantor Request',
                    f'You have been added as a guarantor for {request.user.email}. Please log in to review.',
                    'noreply@bcs.org.ng',
                    [email],
                )

            loan.guarantors_added = True
            loan.status = 'Pending'
            loan.save()
            messages.success(request, "Guarantors added successfully.")
            return redirect('loan:loan_dashboard')
    else:
        form = GuarantorForm(loan_type=loan.loan_type)

    return render(request, 'loan/guarantor_form.html', {'form': form})

from dateutil.relativedelta import relativedelta
from datetime import datetime

@login_required
@user_passes_test(is_employee)
def loan_repayment_setting(request):
    loan = get_object_or_404(Loan, applicant=request.user)

    if request.method == 'POST':
        form = RepaymentSettingForm(request.POST)
        if form.is_valid():
            repayment_setting = form.save(commit=False)
            repayment_setting.loan = loan

            # Convert repayment_start_date from string (YYYY-MM) to datetime
            repayment_start_date_str = form.cleaned_data['repayment_start_date']
            repayment_start_date = datetime.strptime(repayment_start_date_str, "%Y-%m")

            # Calculate repayment_end_date
            repayment_end_date = repayment_start_date + relativedelta(months=loan.repayment_period)

            # Convert both dates back to strings in YYYY-MM format
            repayment_start_date_str = repayment_start_date.strftime("%Y-%m")
            repayment_end_date_str = repayment_end_date.strftime("%Y-%m")

            # Assign values to repayment setting
            repayment_setting.repayment_start_date = repayment_start_date_str
            repayment_setting.repayment_end_date = repayment_end_date_str
            
            repayment_setting.save()

            # Update loan status
            loan.repayment_setting = True
            loan.save()

            messages.success(request, "Repayment settings saved successfully.")
            return redirect('loan:loan_dashboard')
    else:
        form = RepaymentSettingForm()

    return render(request, 'loan/repayment_settings.html', {'form': form})

@login_required
@user_passes_test(is_employee)
def loan_application_complete(request):
    return render(request, 'loan/application_complete.html')


@login_required
def delete_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id, applicant=request.user)

    if not loan.can_be_deleted():
        messages.error(request, "You can only delete a loan application if it is 'Not Finished'.")
        return redirect('loan:loan_dashboard')

    loan.delete()
    messages.success(request, "Loan application deleted successfully.")
    return redirect('loan:loan_dashboard')

@login_required
def cancel_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id, applicant=request.user)

    if not loan.can_be_cancelled():
        messages.error(request, "You can only cancel a loan if it has not been accepted or processed.")
        return redirect('loan:loan_dashboard')

    loan.status = 'Cancelled'
    loan.save()
    messages.success(request, "Loan application cancelled successfully.")
    return redirect('loan:loan_dashboard')


from django.utils import timezone

@login_required
@user_passes_test(is_employee)
def loan_detail(request, loan_id):
    # Fetch the loan using the loan_id
    loan = get_object_or_404(Loan, id=loan_id)

    # Handle approval or rejection with comment
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment')
        guarantor_id = request.POST.get('guarantor_id')
        guarantor = get_object_or_404(Guarantor, id=guarantor_id, loan=loan)

        # Ensure that the currently logged-in user is the guarantor trying to take action
        if guarantor.guarantor == request.user:
            if action and comment:
                # Update the guarantor's status with the comment and action date
                guarantor.status = action
                guarantor.action_note = comment
                guarantor.action_date = timezone.now()
                guarantor.save()

                # Display success message and reload the page
                messages.success(request, f"Guarantor request has been {action.lower()}d.")
                return redirect('loan:loan_detail', loan_id=loan.id)

    context = {
        'loan': loan,
    }

    return render(request, 'loan/loan_detail.html', context)

from accounts.models import CustomUser as User
from django.core.mail import send_mail
from django.contrib import messages

@login_required
@user_passes_test(is_employee)
def add_guarantor(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)

    if request.method == 'POST':
        email_1 = request.POST.get('guarantor_email_1')
        email_2 = request.POST.get('guarantor_email_2')

        # Function to add guarantor based on email
        def add_guarantor_by_email(email):
            try:
                guarantor_user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, f'User with email {email} does not exist.')
                return None
            # Create the guarantor record
            guarantor = Guarantor.objects.create(
                loan=loan,
                guarantor=guarantor_user,
                status='Pending'  # Set initial status to 'Pending'
            )

            # Send email to the newly added guarantor
            send_mail(
                'Guarantor Request',
                f'You have been added as a guarantor for {request.user.email}. Please log in to review.',
                'noreply@bcs.org.ng',  # Sender email
                [email],  # Receiver email
            )

            return guarantor

        # Add guarantors based on remaining slots
        if email_1:
            add_guarantor_by_email(email_1)
        if email_2:
            add_guarantor_by_email(email_2)

        messages.success(request, 'Guarantor(s) added successfully. Emails have been sent.')
        return redirect('loan:loan_dashboard')

    return redirect('loan:loan_dashboard')
