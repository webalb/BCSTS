from django.urls import path
from operations.views import views, admin

urlpatterns = [
    path('dashboard/', views.dashboard, name="dashboard"), 
    path('admin-dashboard/', admin.admin_dashboard, name='admin_dashboard'),
    path('redirect-user/', admin.redirect_user, name='redirect_user'),  # Route for redirection


    path('record-contributions/', views.record_all_contributions, name='record_all_contributions'),
    path('contribution-history/', views.contribution_history, name='contribution_history'),
    path('download-contribution-history/', views.download_contribution_history, name='download_contribution_history'),
    path('contribution-settings/manage/<int:employee_id>/', views.manage_employee_permissions, name='manage_employee_permissions'),

    path('employee/<int:employee_id>/contributions/', views.view_contributions, name='view_contributions'),

    # admin related urls
    path('contribution/', views.contribution_setting_view, name='contribution_setting'),
    path('contribution/manage/', views.manage_contribution_setting, name='manage_contribution_setting'),
    path('contribution/delete/', views.delete_contribution_setting, name='delete_contribution_setting'),
    path('bcs-admin/manage_contributions_settings/', views.manage_employee_contributions, name='manage_employee_contributions'),
    path('bcs-admin/create_contribution_setting/<int:employee_id>/', views.create_contribution_setting, name='create_contribution_setting'),
    path('bcs-admin/update_contribution_setting/<int:pk>/', views.update_contribution_setting, name='update_contribution_setting'),
    path('bce-admin/delete_contribution_setting/<int:pk>/', views.delete_contribution_setting, name='delete_contribution_setting'),

    path('manage-contributions/', views.manage_contributions, name='manage_contributions'),
    path('delete-contribution/<int:contribution_id>/', views.delete_contribution, name='delete_contribution'),
    path('record-contribution/<int:employee_id>/', views.record_individual_contribution, name='record_individual_contribution'),
    path('record-all-missing/', views.record_all_missing_contributions, name='record_all_missing_contributions'),

    path('contribution-history/<int:employee_id>/', views.admin_contribution_history, name='admin_contribution_history'),    
    path('delete-contribution-history/<int:record_id>/', views.delete_contribution_history, name='delete_contribution_history'),
]
