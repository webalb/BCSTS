from django.contrib.auth.decorators import login_required, user_passes_test
from credit.models import Credit, CreditSettings, Guarantor, CreditCommittee
from django.shortcuts import render, get_object_or_404, redirect
from credit.forms import CreditApplicationForm, CreditApplicationForm 
from django.contrib import messages
from operations.utils import get_employee_financial_summary
from credit.utils.utils import *
from django.urls import reverse
from django.db.models import Sum


def is_admin(user):
    return user.groups.filter(name="Admin").exists()

def is_employee(user):
    return user.groups.filter(name="Employee").exists()

@login_required
@user_passes_test(is_employee)
def create_credit_application(request):
    """
    Renders the credit application portal for employees, showing relevant information
    and the employee's current active credit.
    """
    # Get employee's financial summary
    financial_summary = get_employee_financial_summary(request.user)
    total_balance = financial_summary["total_remained_balance"]
    took_credits = financial_summary["took_credits"]
    print(financial_summary)

    # Retrieve the credit settings (Singleton pattern)
    credit_settings = CreditSettings.get_instance()

    # Determine if applications are open today
    is_open_today = credit_settings.is_application_open_today()

    # Enabled credit types
    enabled_credits = {
        "Qard Hasan": credit_settings.enable_qard_hasan,
        "Murabaha": credit_settings.enable_murabaha,
        "Musharaka": credit_settings.enable_musharaka,
        "Ijarah (Lease)": credit_settings.enable_ijarah
    }

    # Retrieve the employee's current active credit (not repaid or cancelled)
    current_credit = Credit.objects.filter(
        applicant=request.user,
        status__in=['Pending', 'Approved', 'Accepted', 'Disbursed'] # Add all active statuses.
    ).first()




    guarantor = None
    committee_info = {}

    if current_credit:
        guarantor = Guarantor.objects.filter(credit=current_credit).first()
        committee_actions_count = current_credit.committee_actions.count() # type: ignore
        newest_action_date = current_credit.committee_actions.order_by('-action_date').first().action_date if committee_actions_count > 0 else None # type: ignore
        if current_credit.status == 'Disbursed' or current_credit.status == 'Repaid':
            transaction_record = current_credit.transactionlog_set.filter(transaction_type='C').first() # type: ignore
            repayment_records = current_credit.repayment_set.all().order_by('-repayment_date') # type: ignore
            total_repaid = repayment_records.aggregate(total=Sum('amount'))['total'] or 0
            
            committee_info = {
            "actions_count": committee_actions_count,
            "newest_action_date": newest_action_date,
            "transaction_record": transaction_record,
            "repayment_records": repayment_records,
            "total_repaid": total_repaid,
            "months_remaining": current_credit.get_remaining_months,
            "total_remaining": Decimal(current_credit.amount_requested) - Decimal(total_repaid), # type: ignore
            }
        else:
            committee_info = {
            "actions_count": committee_actions_count,
            "newest_action_date": newest_action_date
            }

    # Fetch credit requests where the user is a guarantor
    guarantor_requests = Credit.objects.filter(
        guarantors__guarantor=request.user,
        status='Pending'  # Only pending requests
    ).distinct()


    return render(request, 'credit/employee_credit_portal.html', {
        'total_balance': total_balance,
        'is_open_today': is_open_today,
        'enabled_credits': {k: v for k, v in enabled_credits.items() if v},  # Filter enabled types
        'allowed_days': ", ".join(credit_settings.open_days),  # Format allowed days as a string
        'current_credit': current_credit, 
        'guarantor_requests': guarantor_requests,
        "guarantor": guarantor,
        "committee_info": committee_info,
        "took_credits": took_credits,
        "repaid_credits": financial_summary["repaid_credits"],
        "repaid_percentage": financial_summary["repaid_percentage"]
    })

@login_required
@user_passes_test(is_employee)
def credit_policy(request):
    return render(request, 'credit/credit_guidance.html')

@login_required
@user_passes_test(is_admin)
def credit_request(request):
    pending_requests = Credit.objects.filter(status='Pending').order_by('-date_applied')
    return render(request, 'credit/credit_request.html', {
        'pending_requests': pending_requests,
    })


@login_required
def credit_detail(request, tracking_id):
    """
    Displays the details of a specific credit request, including member/user details,
    user account balance, and credit history.
    """
    credit = get_object_or_404(Credit, tracking_id=tracking_id)
    applicant = credit.applicant  # Get the applicant (user)
    financial_metrics = get_employee_financial_summary(applicant)
    applicant_credit_summary = get_applicant_credit_summary(applicant)
    guarantor = Guarantor.objects.filter(credit=credit).first()
    # Fetch committee actions for this credit
    committee_actions = credit.committee_actions.all() # type: ignore
    user_committee_actions = committee_actions.filter(committee_member__member=request.user)
    action_taken = ''
    if user_committee_actions:
        action_taken = user_committee_actions.first().get_action_taken_display()

    committee_info = {}
    if credit:
        guarantor = Guarantor.objects.filter(credit=credit).first()
        committee_actions_count = credit.committee_actions.count() # type: ignore
        newest_action_date = credit.committee_actions.order_by('-action_date').first().action_date if committee_actions_count > 0 else None # type: ignore
        if credit.status == 'Disbursed' or credit.status == 'Repaid':
            transaction_record = credit.transactionlog_set.filter(transaction_type='C').first() # type: ignore
            repayment_records = credit.repayment_set.all().order_by('-repayment_date') # type: ignore
            total_repaid = repayment_records.aggregate(total=Sum('amount'))['total'] or 0
            committee_info = {
            "actions_count": committee_actions_count,
            "newest_action_date": newest_action_date,
            "transaction_record": transaction_record,
            "repayment_records": repayment_records,
            "total_repaid": total_repaid,
            "total_remaining": Decimal(credit.amount_requested) - Decimal(total_repaid), # type: ignore
            }

    if guarantor:
        guarantor_balance = get_employee_financial_summary(guarantor.guarantor)["total_remained_balance"]
    else:
        guarantor_balance = None

    context = {
        'credit': credit,
        'applicant': applicant,
        'financial_metrics': financial_metrics,
        'applicant_credit_summary': applicant_credit_summary,
        'guarantor': guarantor,
        'guarantor_balance': guarantor_balance,
        'committee_actions': committee_actions,
        'action_taken': action_taken,
        'committee_actions_count': committee_actions.count(), # type: ignore
        'committee_count': CreditCommittee.objects.all().count() - 1,  # Exclude the approver
        'committee_info': committee_info
    }

    return render(request, 'credit/credit_detail.html', context)

@login_required
@user_passes_test(is_admin)
def delete_credit_request(request, tracking_id):
    """
    Deletes a credit request.
    """
    credit = get_object_or_404(Credit, tracking_id=tracking_id)

    credit.delete()
    messages.success(request, f'Credit request with tracking ID {tracking_id} deleted successfully.')
    return redirect('credit:credit_request')  # Redirect to the credit requests list

@login_required
@user_passes_test(is_employee)
def credit_application_detail(request, credit_id):
    credit_application = get_object_or_404(Credit, id=credit_id)
    return render(request, 'credit/credit_application_detail.html', {'credit_application': credit_application})

@login_required
@user_passes_test(is_employee)
def credit_application(request, credit_type):
    credit_settings = CreditSettings.get_instance()
    credit_form = CreditApplicationForm(request.POST or None, request.FILES or None)
    total_balance = get_employee_financial_summary(request.user)["total_remained_balance"]

    if request.method == "POST":

        if credit_form.is_valid():
            try:
                guarantor_user = validate_guarantor_email(credit_form.cleaned_data['guarantor_email'])
                validate_repayment_period(credit_form.cleaned_data['repayment_period'], credit_settings.max_repayment_months)
                if credit_type == "Qard Hasan":
                    validate_credit_amount(credit_form.cleaned_data['amount_requested'], credit_settings.min_credit_amount, total_balance * 2)
                if credit_type == "Murabaha":
                    validate_credit_amount(credit_form.cleaned_data['asset_price'], credit_settings.min_credit_amount, total_balance * 2, type="Murabaha")


                credit = save_credit_application(credit_form, request.user, credit_type)
                save_guarantor(credit, guarantor_user)
                notify_admins(
                    heading="New Credit Application",
                    body=f"A new credit application has been submitted by {credit.applicant.full_name()}.",
                    link=reverse("credit:credit_request")
                )

                messages.success(request, "Credit application submitted successfully!")
                return redirect("credit:create_credit_application")

            except ValidationError as e:
                
                # Add the errors to the form's errors dictionary
                if hasattr(e, 'message_dict'): # Check if it's a field error dictionary
                    for field, error in e.message_dict.items():
                        for err in error:
                            credit_form.add_error(field, err)
                else: # Handle non-field errors
                    credit_form.add_error(None, e)

        else:

            messages.error(request, "There was an error with your application. Please check your inputs.")

    return render(request, "credit/application_form.html", {
        "form": credit_form,
        "credit_type": credit_type,
        "credit_settings": credit_settings,
        "total_balance": total_balance
    })

from django.utils import timezone
@login_required
@user_passes_test(is_employee)
def guarantor_action(request, credit_id, action):
    credit = Credit.objects.get(id=credit_id)
    guarantor = Guarantor.objects.get(credit=credit)

    if action == 'approve':
        guarantor.status = 'Approved'
        credit.guarantor_approval = True
        guarantor.action_date = timezone.now()
        notify_committee(credit)
        notify_applicant(
            credit,
            "Guarantor Approved",
            f"Your credit application(#{credit.tracking_id}) passed guarantor approval.",
            reverse("credit:create_credit_application")
            )
        messages.success(request, "You have approved the credit application.")
    elif action == 'decline':
        guarantor.status = 'Declined'
        credit.status = "Rejected"
        guarantor.action_date = timezone.now()
        notify_applicant(
            credit,
            "Guarantor Declined",
            f"Your guarator declined your credit application(#{credit.tracking_id})",
            reverse("credit:create_credit_application")
            )
        messages.success(request, "You have declined the credit application.")

    guarantor.save()
    credit.save()

    return redirect('credit:create_credit_application')


@login_required
@user_passes_test(is_employee)
def committee_credit_request(request):
    """
    View to display credit requests to credit committee members.
    """
    if not request.user.credit_committee_member:
        return render(request, 'errors/403.html', status=403)

    # Filter credit requests that are pending and have guarantor approval
    credit_requests = Credit.objects.filter(status='Pending', guarantor_approval=True)
    context = {
        'credit_requests': credit_requests,
        'is_approver': request.user.credit_committee_member.role == 'Approver',
    }
    return render(request, 'credit/committee_credit_request.html', context)


@login_required
@user_passes_test(is_employee)
def committee_action(request, credit_id):
    """
    View to handle committee actions on credit requests.
    """
    credit = get_object_or_404(Credit, id=credit_id)
    committee_member = request.user.credit_committee_member

    if request.method == 'POST':
        agree_terms = request.POST.get('agree_terms')
        action = request.POST.get('action')

        if not agree_terms:
            messages.error(request, "You must agree to the terms before taking any action.")
            return redirect(request.path)

        if committee_member.role == 'Approver':
            

            if credit.credit_type == "Murabaha":
                profit_margin_percentage = request.POST.get('profit_margin_percentage')
                profit_margin_fixed = request.POST.get('profit_margin_fixed')
                if profit_margin_percentage and profit_margin_fixed:
                    messages.error(request, "Please use only one option for profit margin.")
                    return redirect(request.path)
                if profit_margin_percentage:
                    try:
                        profit_margin_percentage = float(profit_margin_percentage)
                        if profit_margin_percentage > 100:
                            messages.error(request, "Profit margin percentage should be less than or equal to 100.")
                            return redirect(request.path)
                    except ValueError:
                        messages.error(request, "Profit margin percentage should be a number.")
                        return redirect(request.path)
                if profit_margin_fixed:
                    try:
                        profit_margin_fixed = float(profit_margin_fixed)
                    except ValueError:
                        messages.error(request, "Profit margin fixed should be a number.")
                        return redirect(request.path)

                profit_margin = {
                    "type": "percentage" if profit_margin_percentage else "fixed",
                    "value": profit_margin_percentage if profit_margin_percentage else profit_margin_fixed
                }
            else:
                profit_margin = None

            return handle_approver_action(request, committee_member, credit, action, other_type=profit_margin)
        elif committee_member.role == 'Reviewer':
            return handle_reviewer_action(request, committee_member, credit, action)
        else:
            messages.error(request, "Invalid committee member role.")
            return render(request, 'errors/403.html', status=403)

    return redirect('credit:credit_detail', tracking_id=credit.tracking_id)
