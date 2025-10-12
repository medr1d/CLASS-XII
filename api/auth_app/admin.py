from django.contrib import admin
from .models import LoginAttempt, EmailVerification

@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ['ip_address', 'attempted_email', 'timestamp', 'successful']
    list_filter = ['successful', 'timestamp']
    search_fields = ['ip_address', 'attempted_email']
    readonly_fields = ['ip_address', 'attempted_email', 'timestamp', 'successful']
    ordering = ['-timestamp']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'verification_code', 'created_at', 'expires_at', 'verified', 'attempts']
    list_filter = ['verified', 'created_at']
    search_fields = ['email', 'username']
    readonly_fields = ['email', 'username', 'password', 'verification_code', 'created_at', 'expires_at', 'attempts', 'verified']
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
