from django.urls import path
from . import views

app_name = 'auth_app'

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('verify-email/', views.verify_email_view, name='verify_email'),
    path('resend-code/', views.resend_code_view, name='resend_code'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('account/', views.account_view, name='account'),
    path('account/update-theme/', views.update_theme, name='update_theme'),
    path('account/request-password-change/', views.request_password_change, name='request_password_change'),
    path('account/verify-password-change/', views.verify_password_change, name='verify_password_change'),
    path('account/resend-password-change-code/', views.resend_password_change_code, name='resend_password_change_code'),
    path('account/2fa/enable/', views.enable_2fa, name='enable_2fa'),
    path('account/2fa/verify/', views.verify_2fa, name='verify_2fa'),
    path('account/2fa/disable/', views.disable_2fa, name='disable_2fa'),
    path('verify-2fa-login/', views.verify_2fa_login, name='verify_2fa_login'),
    path('api/check-email/', views.check_email_availability, name='check_email'),
    path('api/check-username/', views.check_username_availability, name='check_username'),
    path('admin-panel/', views.admin_panel_view, name='admin_panel'),
    path('api/update-paid-status/', views.update_paid_status, name='update_paid_status'),
    path('api/admin/file/<int:file_id>/', views.get_file_content, name='get_file_content'),
    path('api/admin/file/<int:file_id>/delete/', views.delete_file_admin, name='delete_file_admin'),
]