from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class UserProfile(models.Model):
    THEME_CHOICES = [
        ('default', 'Default (Green Matrix)'),
        ('greydom', 'Greydom (Dark Grey-Blue)'),
        ('cloud', 'Cloud (White & Dark Grey)'),
        ('chaos', 'Chaos (Black & Grey)'),
        ('lebron', 'LeBron (Premium)'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='default')
    paidUser = models.BooleanField(default=False)
    dark_mode_plots = models.BooleanField(default=True)  # New: Dark mode for matplotlib plots
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['paidUser']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

class PythonCodeSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255, default='main.py')
    code_content = models.TextField(blank=True)
    is_auto_save = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'filename']
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['user', 'filename']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.filename}"

class UserFiles(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    file_type = models.CharField(max_length=20, choices=[
        ('text', 'Text File'),
        ('csv', 'CSV File'), 
        ('json', 'JSON File'),
        ('binary', 'Binary File'),
        ('python', 'Python File'),
    ], default='text')
    is_system_file = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'filename']
        ordering = ['filename']
        indexes = [
            models.Index(fields=['user', 'filename']),
            models.Index(fields=['user', 'is_system_file']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.filename}"


class ExecutionHistory(models.Model):
    """Store execution history for code runs"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='execution_history')
    code_snippet = models.TextField()
    output = models.TextField(blank=True)
    error = models.TextField(blank=True)
    execution_time = models.FloatField(default=0)  # milliseconds
    filename = models.CharField(max_length=255, default='untitled.py')
    was_successful = models.BooleanField(default=True)
    executed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['user', '-executed_at']),
            models.Index(fields=['user', 'was_successful']),
            models.Index(fields=['-executed_at']),
        ]
        verbose_name_plural = "Execution Histories"
    
    def __str__(self):
        return f"{self.user.username} - {self.filename} at {self.executed_at.strftime('%Y-%m-%d %H:%M:%S')}"


class SharedCode(models.Model):
    """Allow users to share their code with unique URLs"""
    SESSION_TYPE_CHOICES = [
        ('simple', 'Simple Share (Read-only)'),
        ('collaborative', 'Collaborative Session (Real-time editing)'),
    ]
    
    share_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_codes')
    title = models.CharField(max_length=200)
    code_content = models.TextField()
    description = models.TextField(blank=True)
    language = models.CharField(max_length=20, default='python')
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES, default='simple')
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    view_count = models.IntegerField(default=0)
    fork_count = models.IntegerField(default=0)
    
    # Collaborative session fields
    imported_files = models.JSONField(default=dict, blank=True)  # {filename: content} for owner's imported .py files
    session_state = models.JSONField(default=dict, blank=True)  # Store terminal output, current code state
    members = models.ManyToManyField(User, through='SessionMember', related_name='collaborative_sessions')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['share_id']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_public', '-created_at']),
            models.Index(fields=['-view_count']),
            models.Index(fields=['session_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.title} by {self.user.username}"
    
    def increment_view_count(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def increment_fork_count(self):
        self.fork_count += 1
        self.save(update_fields=['fork_count'])
    
    def is_owner(self, user):
        return self.user == user
    
    def is_expired(self):
        return self.expires_at and timezone.now() > self.expires_at
    
    def is_inactive(self, hours=1):
        """Check if session has been inactive for specified hours"""
        from datetime import timedelta
        if self.session_type != 'collaborative':
            return False
        inactive_threshold = timezone.now() - timedelta(hours=hours)
        return self.last_activity < inactive_threshold
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])
    
    def deactivate_if_inactive(self):
        """Deactivate session if it's been inactive for 1 hour"""
        if self.is_inactive(hours=1) and self.is_active:
            self.is_active = False
            self.save(update_fields=['is_active'])
            return True
        return False


class SessionMember(models.Model):
    """Track members in collaborative sessions"""
    PERMISSION_CHOICES = [
        ('view', 'View Only'),
        ('edit', 'Can Edit'),
    ]
    
    session = models.ForeignKey(SharedCode, on_delete=models.CASCADE, related_name='session_members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='session_memberships')
    permission = models.CharField(max_length=10, choices=PERMISSION_CHOICES, default='view')
    is_online = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    
    
    class Meta:
        unique_together = ['session', 'user']
        indexes = [
            models.Index(fields=['session', 'is_online']),
            models.Index(fields=['user', '-last_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} in {self.session.title} ({self.permission})"


class Friendship(models.Model):
    """Manage friendships between users"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('blocked', 'Blocked'),
    ]
    
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_friend_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_friend_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['from_user', 'to_user']
        indexes = [
            models.Index(fields=['from_user', 'status']),
            models.Index(fields=['to_user', 'status']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.from_user.username} → {self.to_user.username} ({self.status})"
    
    @classmethod
    def are_friends(cls, user1, user2):
        """Check if two users are friends"""
        return cls.objects.filter(
            models.Q(from_user=user1, to_user=user2, status='accepted') |
            models.Q(from_user=user2, to_user=user1, status='accepted')
        ).exists()
    
    @classmethod
    def get_friends(cls, user):
        """Get all friends of a user"""
        friends = cls.objects.filter(
            models.Q(from_user=user, status='accepted') |
            models.Q(to_user=user, status='accepted')
        ).select_related('from_user', 'to_user')
        
        friend_users = []
        for friendship in friends:
            if friendship.from_user == user:
                friend_users.append(friendship.to_user)
            else:
                friend_users.append(friendship.from_user)
        return friend_users


class DirectMessage(models.Model):
    """Direct messages between users"""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['sender', 'recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.sender.username} → {self.recipient.username}: {self.message[:30]}"


class UserStatus(models.Model):
    """Track user online/offline status"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='online_status')
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)
    status_message = models.CharField(max_length=100, blank=True, default='')
    
    class Meta:
        verbose_name_plural = 'User statuses'
        indexes = [
            models.Index(fields=['is_online', '-last_seen']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {'Online' if self.is_online else 'Offline'}"
    
    def update_status(self, is_online=True):
        """Update user online status"""
        self.is_online = is_online
        self.last_seen = timezone.now()
        self.save()



