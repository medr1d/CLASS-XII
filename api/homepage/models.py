from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    THEME_CHOICES = [
        ('default', 'Default (Green Matrix)'),
        ('greydom', 'Greydom (Dark Grey-Blue)'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    theme = models.CharField(max_length=20, choices=THEME_CHOICES, default='default')
    paidUser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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
    
    def __str__(self):
        return f"{self.user.username} - {self.filename}"



