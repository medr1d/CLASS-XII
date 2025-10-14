from django.db import models
from django.contrib.auth.models import User
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
    share_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shared_codes')
    title = models.CharField(max_length=200)
    code_content = models.TextField()
    description = models.TextField(blank=True)
    language = models.CharField(max_length=20, default='python')
    is_public = models.BooleanField(default=True)
    view_count = models.IntegerField(default=0)
    fork_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['share_id']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_public', '-created_at']),
            models.Index(fields=['-view_count']),
        ]
    
    def __str__(self):
        return f"{self.title} by {self.user.username}"
    
    def increment_view_count(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def increment_fork_count(self):
        self.fork_count += 1
        self.save(update_fields=['fork_count'])




