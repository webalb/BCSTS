from django.shortcuts import get_object_or_404
from credit.models import CreditCommittee

def is_credit_committee_member(request):
    """
    Context processor to check if the current user is a credit committee member.
    """
    is_credit_committee = False
    is_approver = False
    is_reviewer = False
    is_admin = False

    if request.user.is_authenticated:
        try:
            member = CreditCommittee.objects.get(member=request.user)
            is_admin = request.user.groups.filter(name="Admin").exists()
            is_credit_committee = True
            is_approver = member.role == 'Approver'
            is_reviewer = member.role == 'Reviewer'
        except CreditCommittee.DoesNotExist:
            is_credit_committee = False
            is_approver = False
            is_reviewer = False
            is_admin = request.user.groups.filter(name="Admin").exists()

    return {'is_credit_committee': is_credit_committee, 'is_approver': is_approver, 'is_reviewer': is_reviewer, 'is_admin': is_admin} # type: ignore
