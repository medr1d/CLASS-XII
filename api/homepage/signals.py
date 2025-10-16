from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, IDEFile
from .achievements import initialize_user_achievements, award_achievement_on_file_creation

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when a new User is created"""
    if created:
        UserProfile.objects.create(user=instance)
        # Initialize achievements for new user
        initialize_user_achievements(instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=UserProfile)
def check_paid_user_achievement(sender, instance, created, **kwargs):
    """Award paid user achievement when profile is updated"""
    from .achievements import check_paid_user
    if instance.paidUser:
        check_paid_user(instance.user)

@receiver(post_save, sender=IDEFile)
def check_beginner_achievement(sender, instance, created, **kwargs):
    """Award beginner achievement when user creates their first file"""
    if created:
        award_achievement_on_file_creation(instance.project.user)
