from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random
import string
import pyotp


class LoginAttempt(models.Model):
    """Track failed login attempts by IP address for rate limiting."""
    ip_address = models.GenericIPAddressField()
    attempted_email = models.EmailField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    successful = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['ip_address', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.ip_address} at {self.timestamp}"
    
    @classmethod
    def is_blocked(cls, ip_address):
        """Check if an IP is blocked due to too many failed attempts."""
        time_threshold = timezone.now() - timedelta(minutes=5)
        recent_attempts = cls.objects.filter(
            ip_address=ip_address,
            timestamp__gte=time_threshold,
            successful=False
        ).count()
        return recent_attempts >= 10
    
    @classmethod
    def get_remaining_attempts(cls, ip_address):
        """Get number of remaining attempts for an IP."""
        time_threshold = timezone.now() - timedelta(minutes=5)
        recent_attempts = cls.objects.filter(
            ip_address=ip_address,
            timestamp__gte=time_threshold,
            successful=False
        ).count()
        return max(0, 10 - recent_attempts)
    
    @classmethod
    def get_time_until_unblock(cls, ip_address):
        """Get time in seconds until IP is unblocked."""
        time_threshold = timezone.now() - timedelta(minutes=5)
        oldest_attempt = cls.objects.filter(
            ip_address=ip_address,
            timestamp__gte=time_threshold,
            successful=False
        ).order_by('timestamp').first()
        
        if oldest_attempt:
            unblock_time = oldest_attempt.timestamp + timedelta(minutes=5)
            remaining = (unblock_time - timezone.now()).total_seconds()
            return max(0, int(remaining))
        return 0
    
    @classmethod
    def cleanup_old_attempts(cls):
        """Remove login attempts older than 24 hours."""
        time_threshold = timezone.now() - timedelta(hours=24)
        cls.objects.filter(timestamp__lt=time_threshold).delete()


class EmailVerification(models.Model):
    """Store email verification codes for new user signups."""
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150)
    password = models.CharField(max_length=128)  # Will store hashed password
    verification_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    verified = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.email} - {'Verified' if self.verified else 'Pending'}"
    
    def save(self, *args, **kwargs):
        if not self.verification_code:
            self.verification_code = self.generate_code()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_code():
        """Generate a random 6-digit verification code."""
        return ''.join(random.choices(string.digits, k=6))
    
    def is_expired(self):
        """Check if the verification code has expired."""
        return timezone.now() > self.expires_at
    
    def is_valid(self, code):
        """Check if the provided code matches and hasn't expired."""
        return (
            self.verification_code == code and
            not self.is_expired() and
            not self.verified and
            self.attempts < 5
        )
    
    def increment_attempts(self):
        """Increment failed verification attempts."""
        self.attempts += 1
        self.save(update_fields=['attempts'])
    
    def mark_verified(self):
        """Mark email as verified."""
        self.verified = True
        self.save(update_fields=['verified'])
    
    @classmethod
    def cleanup_old_verifications(cls):
        """Remove expired verifications older than 1 hour."""
        time_threshold = timezone.now() - timedelta(hours=1)
        cls.objects.filter(created_at__lt=time_threshold, verified=False).delete()
        # Also delete verified ones older than 24 hours
        verified_threshold = timezone.now() - timedelta(hours=24)
        cls.objects.filter(created_at__lt=verified_threshold, verified=True).delete()


class PasswordChangeRequest(models.Model):
    """Store password change verification codes for authenticated users."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_change_requests')
    verification_code = models.CharField(max_length=6)
    new_password = models.CharField(max_length=128)  # Will store hashed new password
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    verified = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {'Verified' if self.verified else 'Pending'}"
    
    def save(self, *args, **kwargs):
        if not self.verification_code:
            self.verification_code = self.generate_code()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_code():
        """Generate a random 6-digit verification code."""
        return ''.join(random.choices(string.digits, k=6))
    
    def is_expired(self):
        """Check if the verification code has expired."""
        return timezone.now() > self.expires_at
    
    def is_valid(self, code):
        """Check if the provided code matches and hasn't expired."""
        return (
            self.verification_code == code and
            not self.is_expired() and
            not self.verified and
            self.attempts < 5
        )
    
    def increment_attempts(self):
        """Increment failed verification attempts."""
        self.attempts += 1
        self.save(update_fields=['attempts'])
    
    def mark_verified(self):
        """Mark code as verified."""
        self.verified = True
        self.save(update_fields=['verified'])
    
    @classmethod
    def cleanup_old_requests(cls):
        """Remove expired password change requests older than 1 hour."""
        time_threshold = timezone.now() - timedelta(hours=1)
        cls.objects.filter(created_at__lt=time_threshold, verified=False).delete()
        # Also delete verified ones older than 24 hours
        verified_threshold = timezone.now() - timedelta(hours=24)
        cls.objects.filter(created_at__lt=verified_threshold, verified=True).delete()


class TwoFactorAuth(models.Model):
    """Store two-factor authentication settings for users."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='two_factor')
    secret_key = models.CharField(max_length=32)  # TOTP secret
    is_enabled = models.BooleanField(default=False)
    backup_codes = models.TextField(blank=True)  # Comma-separated backup codes
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_enabled']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - 2FA {'Enabled' if self.is_enabled else 'Disabled'}"
    
    @staticmethod
    def generate_secret():
        """Generate a new TOTP secret key."""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_backup_codes(count=8):
        """Generate backup codes for 2FA recovery."""
        codes = []
        for _ in range(count):
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            codes.append(f"{code[:4]}-{code[4:]}")
        return codes
    
    def get_backup_codes(self):
        """Return list of backup codes."""
        if self.backup_codes:
            return self.backup_codes.split(',')
        return []
    
    def set_backup_codes(self, codes):
        """Store backup codes as comma-separated string."""
        self.backup_codes = ','.join(codes)
    
    def verify_totp(self, token):
        """Verify a TOTP token."""
        if not self.is_enabled:
            return False
        totp = pyotp.TOTP(self.secret_key)
        return totp.verify(token, valid_window=1)  # Allow 30 seconds window
    
    def verify_backup_code(self, code):
        """Verify and consume a backup code."""
        codes = self.get_backup_codes()
        if code in codes:
            codes.remove(code)
            self.set_backup_codes(codes)
            self.save(update_fields=['backup_codes'])
            return True
        return False
    
    def get_provisioning_uri(self, username):
        """Get provisioning URI for QR code generation."""
        totp = pyotp.TOTP(self.secret_key)
        return totp.provisioning_uri(
            name=username,
            issuer_name='CLASS XII PYTHON'
        )
