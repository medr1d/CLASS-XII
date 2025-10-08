# We'll use Django's built-in User model
# No custom models needed - Django's User model provides:
# - username
# - email
# - password (automatically hashed)
# - first_name, last_name
# - is_active, is_staff, is_superuser
# - date_joined, last_login

# If you need to extend the User model in the future, you can create a Profile model:
# from django.contrib.auth.models import User
# from django.db import models

# class UserProfile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     # Add additional fields here if needed
#     # bio = models.TextField(max_length=500, blank=True)
#     # birth_date = models.DateField(null=True, blank=True)