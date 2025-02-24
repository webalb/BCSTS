from django.urls import path
from . import views

app_name="withdrawal"

urlpatterns = [
    path('bank-details/add/', views.add_account, name='add_account'),
    path('bank-details/delete/<int:pk>/', views.delete_account, name='delete_account'),

    path("admin-withdrawals-management/", views.admin_withdrawal_management, name="admin_withdrawal_management"),
    path("employee-withdrawals-management/", views.employee_withdrawal_management, name="employee_withdrawal_management"),

    path('update-charge/', views.update_charge, name='update_charge'),
    path('charge-management/', views.charge_management, name='charge_management'),

    # # withdrawal request process urls
    path("request/", views.withdrawal_request, name="withdrawal_request"),
    path('request-cancel/<int:request_id>/', views.cancel_request, name='cancel_request'),
    
    path('approve/<int:request_id>/', views.approve_request, name='approve_request'),
    path('decline/<int:request_id>/', views.decline_request, name='decline_request'),
    path('pay/<int:request_id>/', views.pay_request, name='pay_request'),
    path('update-withdrawal-status/', views.update_withdrawal_status, name='update_withdrawal_status'),


    # path('withdrawals/<int:transaction_id>/receipt/', views.download_receipt, name='download_receipt'),

]
