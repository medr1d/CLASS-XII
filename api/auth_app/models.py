from django.db import models
from django.utils import timezone

class LoginAttempt(models.Model):
    """Track failed login attempts by IP address for rate limiting"""
    ip_address = models.GenericIPAddressField()
    attempted_at = models.DateTimeField(auto_now_add=True)
    email = models.EmailField(blank=True, null=True)
    
    class Meta:
        app_label = 'auth_app'
        ordering = ['-attempted_at']
        indexes = [
            models.Index(fields=['ip_address', 'attempted_at']),
        ]
    
    def __str__(self):
        return f"{self.ip_address} at {self.attempted_at}"
    
    @classmethod
    def is_blocked(cls, ip_address, max_attempts=10, time_window_minutes=5):
        """Check if an IP address should be blocked due to too many failed attempts"""
        time_threshold = timezone.now() - timezone.timedelta(minutes=time_window_minutes)
        recent_attempts = cls.objects.filter(
            ip_address=ip_address,
            attempted_at__gte=time_threshold
        ).count()
        return recent_attempts >= max_attempts
    
    @classmethod
    def record_attempt(cls, ip_address, email=None):
        """Record a failed login attempt"""
        return cls.objects.create(ip_address=ip_address, email=email)
    
    @classmethod
    def clear_old_attempts(cls, days=7):
        """Remove old login attempts to keep the database clean"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        return cls.objects.filter(attempted_at__lt=cutoff_date).delete()