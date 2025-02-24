from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from credit.models import CreditCommittee, CreditSettings
from credit.forms import CreditCommitteeForm, CreditSettingsForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from accounts.models import CustomUser
from django.core.mail import send_mail
from django.conf import settings
from notification.models import Notification
from notification.services import NotificationService

def is_admin(user):
    return user.groups.filter(name="admin").exists()

def is_employee(user):
    return user.groups.filter(name="Employee").exists()


def get_members_without_credit_committee():
    """
    Fetches CustomUsers who are NOT superusers, NOT in 'Admin' group,
    and do NOT have a CreditCommittee object.
    """

    admin_group = Group.objects.filter(name="Admin").first()

    users = CustomUser.objects.filter(credit_committee_member__isnull=True).exclude(is_superuser=True)

    if admin_group:
        users = users.exclude(groups=admin_group)

    return users

@login_required
@user_passes_test(is_admin)
def credit_settings(request):
    settings_instance = CreditSettings.get_instance()  # Always get the single instance

    # Fetch all committee members
    committee_members = CreditCommittee.objects.select_related('member').all()

    # Initialize forms
    form = CreditSettingsForm(instance=settings_instance)
    committee_form = CreditCommitteeForm()

    if request.method == 'POST':
        if 'settings_submit' in request.POST:  # Credit Settings Form submission
            form = CreditSettingsForm(request.POST, instance=settings_instance)
            if form.is_valid():
                form.save()
                messages.success(request, "Credit settings updated successfully.")
                return redirect('credit:credit_settings')
            else:
                messages.error(request, "Please correct the errors below.")

        elif 'committee_submit' in request.POST:  # Committee Form submission
            committee_form = CreditCommitteeForm(request.POST)
            if committee_form.is_valid():
                committee_member = committee_form.save()

                # Send Notifications
                user = committee_member.member
                link = ""

                # In-App Notification
                NotificationService.send_notification(
                    user,
                    "Welcome to BCS  Credit Committee",
                    "Congratulations! You have been added as a credit committee member in BCS.",
                    link,
                    notification_type=Notification.NotificationType.IN_APP
                )

                # Email Notification
                subject = "BCS Committee Membership"
                message = f"Dear {user.get_full_name()},\n\nYou have been added as a committee member in BCS. Please log in to your account to check your responsibilities.\n\nBest regards,\nBCS Team"
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

                messages.success(request, "New committee member added successfully.")
                return redirect('credit:credit_settings')
            else:
                messages.error(request, "Error adding committee member. Please check the form.")


    return render(request, 'credit/setting/settings.html', {
        'form': form,
        'committee_form': committee_form,
        'committee_members': committee_members,
        'members': get_members_without_credit_committee()
    })

from django.http import HttpResponseForbidden

@login_required
@user_passes_test(is_admin)
def remove_credit_committee_member(request, member_id):
    """
    Removes a user from the CreditCommittee and sends a notification.
    """
    member = get_object_or_404(CreditCommittee, id=member_id)
    user = member.member 
    member.delete()

    link = "" # Adjust link as needed

    NotificationService.send_notification(
        user,
        "Credit Committee Membership Removed",
        "You have been removed from the credit committee in BCS.",
        link,
        notification_type=Notification.NotificationType.IN_APP
    )
    messages.success(request, f"The credit committee member {user.get_full_name()} has been successfully removed.")
    return redirect('credit:credit_settings') # Replace with your URL name