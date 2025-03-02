from tkinter import NO
from django.contrib import messages
from django.shortcuts import redirect
from django.core.exceptions import ValidationError
from credit.models import Credit, Murabaha, Musharaka, Ijarah, Guarantor, CommitteeAction
from accounts.models import CustomUser
from notification.services import NotificationService
from notification.models import Notification
from django.urls import reverse
from operations.utils import get_employee_financial_summary, get_system_financial_summary

from django.core.exceptions import ValidationError

def validate_guarantor_email(email):
    guarantor_user = CustomUser.objects.filter(email=email).first()
    if not guarantor_user:
        raise ValidationError({'guarantor_email': "Invalid guarantor email address. Please enter a valid registered email."})
    return guarantor_user

def validate_repayment_period(repayment_period, max_repayment_months):
    if repayment_period > max_repayment_months:
        raise ValidationError({'repayment_period': f"Repayment period cannot exceed {max_repayment_months} months."})

def validate_credit_amount(amount, min_amount, max_amount, type="Qard Hasan"):
    if not (min_amount <= amount <= max_amount):
        if type=="Qard Hasan":
            raise ValidationError({'amount_requested': f"Invalid credit amount. Must be between NGN{min_amount} and NGN{max_amount}."})
        raise ValidationError({'asset_price': f"Invalid asset price. Must be between NGN{min_amount} and NGN{max_amount}."})

def validate_vendor_invoice(vendor_invoice):
    allowed_extensions = ["pdf"]
    if vendor_invoice and vendor_invoice.name.split(".")[-1].lower() not in allowed_extensions:
        raise ValidationError({'vendor_invoice': "Invalid file format for vendor invoice. Only PDF file is allowed."})

def save_credit_application(form, user, credit_type):
    try:
        credit = form.save(commit=False)
        credit.applicant = user
        credit.credit_type = credit_type
        if credit_type == "Qard Hasan":
            credit.amount_requested = form.cleaned_data['amount_requested']
        elif credit_type == "Murabaha": 
            credit.amount_requested = form.cleaned_data['asset_price']
        credit.status = "Pending"
        credit.save()

        if credit_type == 'Murabaha':
            vendor_invoice = form.cleaned_data["vendor_invoice"]
            validate_vendor_invoice(vendor_invoice)

            Murabaha.objects.create(
                credit=credit,
                asset_name=form.cleaned_data['asset_name'],
                asset_price=form.cleaned_data['asset_price'],
                vendor_invoice=vendor_invoice
            )
        elif credit_type == 'Musharaka':
            Musharaka.objects.create(
                credit=credit,
                partner_contribution=form.cleaned_data['partner_contribution'],
                profit_sharing_ratio=form.cleaned_data['profit_sharing_ratio']
            )
        elif credit_type == 'Ijarah':
            Ijarah.objects.create(
                credit=credit,
                lease_period=form.cleaned_data['lease_period'],
                rental_amount=form.cleaned_data['rental_amount']
            )

        return credit

    except ValidationError as e:
        # Re-raise the ValidationError to be handled in the view
        raise e
def save_guarantor(credit, guarantor_user):
    """
    Save the guarantor and send notifications.
    """
    Guarantor.objects.create(
        credit=credit,
        guarantor=guarantor_user,
        status="Pending",
    )
    NotificationService.send_notification(
        guarantor_user,
        "Guarantor Request",
        f"You have been requested as a guarantor for {credit.applicant.get_full_name()} in his/her credit application.",
        link=reverse("credit:create_credit_application"),
        notification_type=Notification.NotificationType.IN_APP
    )

def notify_admins(heading, body, link):
    """
    Notify admin users.
    """
    admin_users = CustomUser.objects.filter(groups__name="Admin")
    for admin in admin_users:
        NotificationService.send_notification(
            admin,
            heading,
            body,
            link=link,
            notification_type=Notification.NotificationType.IN_APP
        )

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from decimal import Decimal


def get_applicant_credit_summary(applicant):
    """
    Returns a dictionary with the count of credit applications, approved, disbursed,
    and repayment percentage for a specific applicant.
    """

    # Optimized query to get counts
    credit_summary = Credit.objects.filter(applicant=applicant).aggregate(
        applications=Count('id'),
        disbursed=Count('id', filter=Q(status='Disbursed')),
        repaid=Count('id', filter=Q(status='Repaid')),
    )
    financial_metrics = get_employee_financial_summary(applicant)
    
    return {
        'applications': credit_summary['applications'],
        'disbursed': credit_summary['disbursed'],
        'repaid': credit_summary['repaid'],
        'repayment_percentage': financial_metrics['repaid_percentage'], # round to 2 places.
    }


def get_system_credit_summary():
    """
    Returns a dictionary with the count of total applications, approved, disbursed,
    and repayment percentage for the entire system.
    """

    # Optimized query to get counts and sums
    credit_summary = Credit.objects.aggregate(
        applications=Count('id'),
        disbursed=Count('id', filter=Q(status='Disbursed')),
        repaid=Count('id', filter=Q(status='Repaid')),
    )
    financial_metrics = get_system_financial_summary()
    
    return {
        'applications': credit_summary['applications'],
        'disbursed': credit_summary['disbursed'],
        'repaid': credit_summary['repaid'],
        'repayment_percentage': financial_metrics['repaid_percentage'], # round to 2 places.
    }


from credit.models import CreditCommittee
from accounts.models import CustomUser

def notify_committee(credit):
    """
    Notify Credit Committee members about a new credit request that passed guarantor approval.
    """
    committee_members = CreditCommittee.objects.all() # Get all committee members
    for member in committee_members:
        NotificationService.send_notification(
            member.member,
            "New Credit Request (Guarantor Approved)",
            f"A credit request from {credit.applicant.get_full_name()} has passed guarantor approval and requires commitee review.",
            link=reverse("credit:credit_detail", kwargs={'tracking_id': credit.tracking_id}), # link to credit detail.
            notification_type=Notification.NotificationType.IN_APP
        )

def notify_applicant(credit, heading, body, link):
    """
    Notify Credit Committee members about a new credit request that passed guarantor approval.
    """
    NotificationService.send_notification(
        credit.applicant,
        heading,
        body,
        link,
        notification_type=Notification.NotificationType.IN_APP
    )
def notify_committee_members(heading, body, link):
    """
    Notify all committee members about a new credit request.
    """
    committee_members = CreditCommittee.objects.all()
    for member in committee_members:
        NotificationService.send_notification(
            member.member,
            heading,
            body,
            link,
            notification_type=Notification.NotificationType.IN_APP
        )


def handle_approver_action(request, committee_member, credit, action, other_type=None):
    """
    Handle actions taken by approvers.
    """
    if not all_reviewers_reviewed(credit):
        messages.error(request, "All reviewers must review the request before an approver can take action.")
        return redirect(request.path)

    if action == 'approve':
        process_approval(request, committee_member, credit, other_type)
    elif action == 'decline':
        process_decline(request, committee_member, credit)
    else:
        messages.error(request, "Invalid action for approver.")
        return redirect('committee_credit_request')

    credit.save()
    return redirect('credit:committee_credit_request')

def all_reviewers_reviewed(credit):
    """
    Check if all reviewers have reviewed the request.
    """
    total_reviewers = CreditCommittee.objects.filter(role='Reviewer').count()
    reviewed_count = CommitteeAction.objects.filter(credit=credit, action_taken__in=['Okay', 'Not Okay']).count()
    return reviewed_count >= total_reviewers

def process_approval(request, committee_member, credit, other_type=None):
    """
    Process credit approval.
    """
    credit.status = 'Approved'
    create_committee_action(committee_member, credit, 'Approved', other_type)
    send_notifications('Credit Approved', credit)
    messages.success(request, "Credit request has been approved.")

def process_decline(request, committee_member, credit):
    """
    Process credit decline.
    """
    credit.status = 'Rejected'
    create_committee_action(committee_member, credit, 'Declined')
    send_notifications('Credit Declined', credit)
    messages.success(request, "Credit request has been declined.")

def handle_reviewer_action(request, committee_member, credit, action):
    """
    Handle actions taken by reviewers.
    """
    if action == 'okay':
        create_committee_action(committee_member, credit, 'Okay')
        messages.success(request, "You voted Okay.")
    elif action == 'not_okay':
        create_committee_action(committee_member, credit, 'Not Okay')
        messages.success(request, "You voted Not Okay.")
    else:
        messages.error(request, "Invalid action for reviewer.")
        return redirect(request.path)
    
    send_notifications(f"Credit Reviewed - {action.title().replace('_', ' ')}", credit)
    credit.save()
    return redirect('credit:committee_credit_request')

def create_committee_action(committee_member, credit, action_taken, other_type=None):
    """
    Create a CommitteeAction entry.
    """
    if other_type:
        if credit.credit_type == "Murabaha":
            murabaha = credit.get_credit_type_model
            if other_type["type"] == "percentage":
                murabaha.profit_margin_percentage = int(other_type["value"])
            else:
                murabaha.profit_margin_fixed = other_type["value"]
            murabaha.save()
          
    CommitteeAction.objects.create(
        committee_member=committee_member,
        action_taken=action_taken,
        action_reason=f"Reviewed and voted {action_taken}",
        credit=credit
    )
    return

def send_notifications(heading, credit):
    """
    Send notifications to admins, applicants, and committee members.
    """
    notify_admins(
        heading=heading,
        body=f"The credit application(#{credit.tracking_id}) has been {heading.lower()} by the committee.",
        link=reverse("credit:credit_request")
    )
    notify_applicant(
        credit,
        f"Committee {heading}",
        f"Your credit application(#{credit.tracking_id}) has been {heading.lower()} by the committee.",
        reverse("credit:create_credit_application")
    )
    notify_committee_members(
        heading=heading,
        body=f"The credit application(#{credit.tracking_id}) has been {heading.lower()} by the committee.",
        link=reverse("credit:committee_credit_request")
    )

