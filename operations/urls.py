from django.urls import path
from operations.views import views, admin, target
from operations.views import bulk_upload_contributions, confirm_bulk_upload

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name="dashboard"), 
    path('admin-dashboard/', admin.admin_dashboard, name='admin_dashboard'),
    path('redirect-user/', admin.redirect_user, name='redirect_user'),  # Route for redirection

    path('record-contributions/', admin.record_all_contributions, name='record_all_contributions'),

    path('contributor/<str:employee_id>/contributions/', views.view_contributions, name='view_contributions'),
    path('bcs-contributor/<str:employee_id>/contributions/', admin.view_employee_contributions, name='view_employee_contributions'),
    path('contributions-settings/', views.contribution_setting_history, name='contribution_setting_history'),

    path("requests-contribution-change/", views.request_contribution_change, name="request_contribution_change"),
    path("process-request/<str:request_id>/<str:action>/", admin.process_contribution_request, name="process_contribution_request"),

    # admin related urls
    path('bcs-admin/manage_contributions_settings/', admin.manage_employee_contributions, name='manage_employee_contributions'),
    path('bcs-admin/create_contribution_setting/<str:employee_id>/', admin.create_contribution_setting, name='create_contribution_setting'),
    path('bcs-admin/update_contribution_setting/<str:pk>/', admin.update_contribution_setting, name='update_contribution_setting'),
    path('bce-admin/delete_contribution_setting/<str:pk>/', admin.delete_contribution_setting, name='delete_contribution_setting'),

    path('manage-contributions/', admin.manage_contributions, name='manage_contributions'),
    path('delete-contribution/<str:contribution_id>/', admin.delete_contribution, name='delete_contribution'),
    path('record-contribution/<str:employee_id>/', admin.record_individual_contribution, name='record_individual_contribution'),
    path('record-all-missing/', admin.record_all_missing_contributions, name='record_all_missing_contributions'),

    # admin to view all contribution history for employee
    path('contribution-history/<str:employee_id>/', admin.admin_contribution_history, name='admin_contribution_history'),    
    path('delete-contribution-history/<str:record_id>/', admin.delete_contribution_history, name='delete_contribution_history'),

    path('upload-contributions/', bulk_upload_contributions, name='bulk_upload_contributions'),
    path('confirm-bulk-upload/', confirm_bulk_upload, name='confirm_bulk_upload'),

    path('api/monthly-contributions/', admin.get_monthly_contributions, name='monthly_contributions'),


    path('targets/', target.member_target_savings_page, name='member_target_savings_page'),
    path('completed-targets/', target.completed_target_savings, name='completed_target_savings'),
    path('contributors-targets/', target.admin_target_savings_page, name='admin_target_savings_page'),
    path('target/<str:target_id>/', target.target_savings_detail, name='target_savings_detail'),
    path('my-target/<str:target_id>/', target.member_target_detail, name='member_target_detail'),
    path('target-savings/withdrawal/<str:target_id>/', target.request_target_withdrawal, name='request_target_withdrawal'),
]
