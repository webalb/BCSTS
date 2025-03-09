from django.urls import path
from credit.views import settings, credit, disbursement

app_name="credit"

urlpatterns = [ 


    path("credit-settings/", settings.credit_settings, name="credit_settings"),
    path('credit-committee/remove/<int:member_id>/', settings.remove_credit_committee_member, name='remove_credit_committee_member'),


    path('create_credit_application/', credit.create_credit_application, name='create_credit_application'),
    path('credit_application/<int:credit_id>/', credit.credit_application_detail, name='credit_application_detail'),  # Optional detail view
    path('BCS-credit-policy/', credit.credit_policy, name='credit_policy'),  # Optional detail view

    path('apply/<str:credit_type>/', credit.credit_application, name='apply_credit'),
    path('credit-request/', credit.credit_request, name='credit_request'),

    path('request/<str:tracking_id>/', credit.credit_detail, name='credit_detail'),
    path('request/<str:tracking_id>/delete/', credit.delete_credit_request, name='delete_credit_request'),
    path('guarantor-action/<int:credit_id>/<str:action>/',credit.guarantor_action, name='guarantor_action'),


    path('committee/credit-requests/', credit.committee_credit_request, name='committee_credit_request'),
    path('committee/action/<int:credit_id>/', credit.committee_action, name='committee_action'),
    
    path('approved-credit-request/', disbursement.approved_credit_requests, name='approved_credit_request'),

    path('disburse-credit/<str:tracking_id>/', disbursement.disburse_credit, name='disburse_credit'),
    path('disbursed-credits/', disbursement.disbursed_credits, name='disbursed_credits'),
    path('clear-credit/<str:tracking_id>/', disbursement.clear_credit, name='clear_credit'),

    path('record-credit-repayments/', settings.record_monthly_repayment, name='record_monthly_repayment'),
    path('accept-or-reject/<str:tracking_id>/', disbursement.accept_or_reject, name='accept_or_reject'),
    path('credit_history/', disbursement.credit_history, name='credit_history'),

]



