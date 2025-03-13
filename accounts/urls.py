from django.urls import path
from django.contrib.auth import views as auth_views

from .views import (logout_view, change_password, my_login_view, 
    employee_list, create_employee, update_employee, delete_employee, 
    employee_detail, toggle_employee_active,employee_specific_detail, view_mcr, account_settings,
     bulk_upload_users, confirm_bulk_user_upload, update_employee_date_joined,
       admin_reset_member_password, generate_and_download_backup)

urlpatterns = [
    path("login/", my_login_view, name="login"),
    path("logout/", logout_view, name="logout"),

    path("password_reset/", auth_views.PasswordResetView.as_view(template_name="accounts/password_reset.html"), name="password_reset"),
    path("password_reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="accounts/password_reset_confirm.html"), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"), name="password_reset_complete"),
    path('change-password/', change_password, name='change_password'),

    path('', employee_list, name='employee_list'),
    path('create/', create_employee, name='create_employee'),
    path('update/<str:employee_id>/', update_employee, name='update_employee'),
    path('delete/<str:employee_id>/', delete_employee, name='delete_employee'),
    path('details/<str:employee_id>/', employee_detail, name='employee_detail'),
    path('my-details/<str:employee_id>/', employee_specific_detail, name='employee_specific_detail'),

    path('toggle_active/<str:employee_id>/', toggle_employee_active, name='toggle_employee_active'),

    path('member/<int:nitda_id>/mcr/', view_mcr, name='view_mcr'),

    path('settings', account_settings, name='settings'),

    path("bulk-upload-users/", bulk_upload_users, name="bulk_upload_users"),
    path("confirm-bulk-upload-users/", confirm_bulk_user_upload, name="confirm_bulk_user_upload"),

    path('update-date-joined/', update_employee_date_joined, name='update_date_joined'),
    path('reset-contributor--password/<str:employee_id>/', admin_reset_member_password, name='admin_reset_member_password'),

    path('generate_and_download_backup/', generate_and_download_backup, name='generate_and_download_backup'),

]
