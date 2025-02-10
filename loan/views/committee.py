from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from loan.models import LoanCommittee
from loan.forms import LoanCommitteeForm
from django.contrib.auth.decorators import login_required, user_passes_test

def is_admin(user):
    return user.groups.filter(name="admin").exists()

def is_employee(user):
    return user.groups.filter(name="Employee").exists()

@login_required
@user_passes_test(is_admin)
def admin_loan_dashboard(request):
    return render(request, 'loan/admin_loan_dashboard.html')

@login_required
@user_passes_test(is_admin)
def committee_list(request):
    committees = LoanCommittee.objects.all()
    return render(request, 'loan/committee/committee_list.html', {'committees': committees})

@login_required
@user_passes_test(is_admin)
def committee_add(request):
    if request.method == 'POST':
        form = LoanCommitteeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Committee member added successfully!")
            return redirect('loan:committee_list')
    else:
        form = LoanCommitteeForm()
    return render(request, 'loan/committee/committee_form.html', {'form': form, 'title': 'Add Committee Member'})

@login_required
@user_passes_test(is_admin)
def committee_edit(request, pk):
    committee = get_object_or_404(LoanCommittee, pk=pk)
    if request.method == 'POST':
        form = LoanCommitteeForm(request.POST, instance=committee)
        if form.is_valid():
            form.save()
            messages.success(request, "Committee member updated successfully!")
            return redirect('loan:committee_list')
    else:
        form = LoanCommitteeForm(instance=committee)
    return render(request, 'loan/committee/committee_form.html', {'form': form, 'title': 'Edit Committee Member'})

@login_required
@user_passes_test(is_admin)
def committee_delete(request, pk):
    committee = get_object_or_404(LoanCommittee, pk=pk)
    if request.method == 'POST':
        committee.delete()
        messages.success(request, "Committee member deleted successfully!")
        return redirect('loan:committee_list')
    return render(request, 'loan/committee/committee_confirm_delete.html', {'committee': committee})
