from django.contrib.auth.views import LoginView
from django.urls import path
from django.contrib.auth import views as auth_views

from .views import register, activate_email, logout_view, change_password, my_login_view, employee_list, create_employee, update_employee, delete_employee, employee_detail

urlpatterns = [
    path("register/", register, name="register"),
    path("activate/<uidb64>/<token>/", activate_email, name="activate_email"),
    path("login/", my_login_view, name="login"),
    path("logout/", logout_view, name="logout"),


    path("password_reset/", auth_views.PasswordResetView.as_view(template_name="accounts/password_reset.html"), name="password_reset"),
    path("password_reset/done/", auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="accounts/password_reset_confirm.html"), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"), name="password_reset_complete"),
    path('change-password/', change_password, name='change_password'),

    path('', employee_list, name='employee_list'),
    path('create/', create_employee, name='create_employee'),
    path('update/<int:employee_id>/', update_employee, name='update_employee'),
    path('delete/<int:employee_id>/', delete_employee, name='delete_employee'),
    path('details/<int:employee_id>/', employee_detail, name='employee_detail'),


]
