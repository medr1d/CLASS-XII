from django.urls import path
from . import views

app_name = 'auth_app'

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('account/', views.account_view, name='account'),
    path('api/check-email/', views.check_email_availability, name='check_email'),
    path('api/check-username/', views.check_username_availability, name='check_username'),
]