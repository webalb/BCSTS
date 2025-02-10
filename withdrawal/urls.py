from django.urls import path
from . import views

app_name="withdrawal"

urlpatterns = [
    path('bank-details/add/', views.add_account, name='add_account'),
    path('bank-details/delete/<int:pk>/', views.delete_account, name='delete_account'),

    path('charges/create/', views.withdrawal_charge_create, name='charge_create'),
    path('charges/delete/<int:pk>/',views. withdrawal_charge_delete, name='charge_delete'),

    # withdrawal request process urls
    path('policy/', views.withdrawal_policy, name='policy'),
    path('request/', views.withdrawal_request_form, name='request_form'),
    path('upload/<int:withdrawal_request_id>/', views.upload_document, name='upload_documents'),
    path('completed/', views.completed, name='completed'),
    path('cancel_withdrawal_request/', views.cancel_withdrawal_request, name='cancel_withdrawal_request'),
    
    path('requests/', views.withdrawal_requests_list, name='withdrawal_requests_list'),
    path('delete/<int:withdrawal_request_id>/', views.delete_withdrawal_request, name='delete_withdrawal_request'),

    path('approve/<int:request_id>/', views.approve_withdrawal_request, name='approve_withdrawal_request'),
    path('reject/<int:request_id>/', views.reject_withdrawal_request, name='reject_withdrawal_request'),
    path('process/<int:request_id>/', views.process_payment, name='process_payment'),


    path('all/transactions/', views.admin_transactions, name='admin_transactions'),
    path('my-transactions/', views.employee_transactions, name='employee_transactions'),

    path('withdrawals/<int:transaction_id>/receipt/', views.download_receipt, name='download_receipt'),

]
