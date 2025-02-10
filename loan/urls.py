from django.urls import path
from loan.views import committee, loan

app_name="loan"

urlpatterns = [
    path('admin_dashboard/', committee.admin_loan_dashboard, name='admin_loan_dashboard'),
    path('dashboard/', loan.loan_dashboard, name='loan_dashboard'),

    path('committees/', committee.committee_list, name='committee_list'),
    path('committees/add/', committee.committee_add, name='committee_add'),
    path('committees/edit/<int:pk>/', committee.committee_edit, name='committee_edit'),
    path('committees/delete/<int:pk>/', committee.committee_delete, name='committee_delete'),

    path('loan-guidance/', loan.loan_guidance, name='loan_guidance'),
    path('apply-loan/', loan.loan_application, name='loan_application'),
    path('details/', loan.loan_details, name='loan_details'),
    path('guarantors/', loan.loan_guarantors, name='loan_guarantors'),
    path('repayment/', loan.loan_repayment_setting, name='loan_repayment_setting'),
    path('complete/', loan.loan_application_complete, name='loan_application_complete'),

    path('loan/delete/<int:loan_id>/', loan.delete_loan, name='delete_loan'),
    path('loan/cancel/<int:loan_id>/', loan.cancel_loan, name='cancel_loan'),

    path('loan/<int:loan_id>/detail/', loan.loan_detail, name='loan_detail'),
    path('loan/<int:loan_id>/add_guarantor/', loan.add_guarantor, name='add_guarantor'),

]



