"""
Achievement System - Utility functions for awarding and checking achievements
"""
from django.contrib.auth.models import User
from .models import Achievement, UserAchievement, UserProfile, IDEFile


def check_and_award_achievement(user, achievement_type):
    """
    Check if user qualifies for an achievement and award it if they don't have it
    Returns True if achievement was awarded, False otherwise
    """
    try:
        achievement = Achievement.objects.get(achievement_type=achievement_type, is_active=True)
        
        # Check if user already has this achievement
        if UserAchievement.objects.filter(user=user, achievement=achievement).exists():
            return False
        
        # Award the achievement
        UserAchievement.objects.create(user=user, achievement=achievement)
        return True
        
    except Achievement.DoesNotExist:
        return False


def check_og_user(user):
    """Check if user should get OG User achievement (first 100 users)"""
    try:
        profile = UserProfile.objects.get(user=user)
        # Count users created before this user
        earlier_users = User.objects.filter(date_joined__lt=user.date_joined).count()
        
        if earlier_users < 100:
            return check_and_award_achievement(user, 'og_user')
    except UserProfile.DoesNotExist:
        pass
    
    return False


def check_paid_user(user):
    """Check if user should get Paid User achievement"""
    try:
        profile = UserProfile.objects.get(user=user)
        if profile.paidUser:
            return check_and_award_achievement(user, 'paid_user')
    except UserProfile.DoesNotExist:
        pass
    
    return False


def check_beginner(user):
    """Check if user should get Beginner achievement (created first file)"""
    # Check if user has created any file
    file_count = IDEFile.objects.filter(project__user=user).count()
    
    if file_count >= 1:
        return check_and_award_achievement(user, 'beginner')
    
    return False


def award_achievement_on_file_creation(user):
    """Called when a user creates their first file"""
    check_beginner(user)


def initialize_user_achievements(user):
    """Initialize achievements for a user (called on signup or profile creation)"""
    check_og_user(user)
    check_paid_user(user)
    # Beginner is awarded when they create their first file


def get_user_achievements(user, displayed_only=False, limit=None):
    """
    Get achievements for a user
    
    Args:
        user: The user to get achievements for
        displayed_only: If True, only return achievements marked for display
        limit: Maximum number of achievements to return
    
    Returns:
        QuerySet of UserAchievement objects with related achievement data
    """
    query = UserAchievement.objects.filter(user=user)
    
    if displayed_only:
        query = query.filter(is_displayed=True)
    
    query = query.select_related('achievement').order_by('-earned_at')
    
    if limit:
        query = query[:limit]
    
    # Return values with achievement fields for easy template access
    return query.values(
        'id',
        'earned_at',
        'is_displayed',
        'achievement__name',
        'achievement__description',
        'achievement__badge_icon',
        'achievement__points'
    )


def get_user_achievement_count(user):
    """Get count of achievements for a user"""
    return UserAchievement.objects.filter(user=user).count()


def create_default_achievements():
    """Create the default achievements if they don't exist"""
    achievements = [
        {
            'achievement_type': 'og_user',
            'name': 'OG User',
            'description': 'One of the first 100 users to join the platform',
            'badge_icon': 'og_user.png',
            'points': 50
        },
        {
            'achievement_type': 'paid_user',
            'name': 'Paid User',
            'description': 'Unlocked premium features with paid access',
            'badge_icon': 'paid_user.png',
            'points': 25
        },
        {
            'achievement_type': 'beginner',
            'name': 'Beginner',
            'description': 'Created your first file in the IDE',
            'badge_icon': 'beginner.png',
            'points': 10
        },
    ]
    
    for achievement_data in achievements:
        Achievement.objects.get_or_create(
            achievement_type=achievement_data['achievement_type'],
            defaults=achievement_data
        )
