"""
Management command to debug and fix achievement system
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from homepage.models import Achievement, UserAchievement, UserProfile, IDEFile
from homepage.achievements import create_default_achievements, check_og_user, check_paid_user, check_beginner


class Command(BaseCommand):
    help = 'Debug and fix achievement system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username to check (optional, checks all if not provided)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-award achievements (removes existing ones first)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== ACHIEVEMENT SYSTEM DEBUG ===\n'))
        
        # Step 1: Create default achievements
        self.stdout.write('Step 1: Creating default achievements...')
        create_default_achievements()
        
        achievements = Achievement.objects.all()
        self.stdout.write(self.style.SUCCESS(f'✓ Found {achievements.count()} achievements:'))
        for ach in achievements:
            self.stdout.write(f'  - {ach.achievement_type}: {ach.name} ({ach.points} pts)')
        
        # Step 2: Check specific user or all users
        if options['username']:
            try:
                user = User.objects.get(username=options['username'])
                users = [user]
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'✗ User "{options["username"]}" not found'))
                return
        else:
            users = User.objects.all()
        
        self.stdout.write(f'\nStep 2: Checking {users.count() if hasattr(users, "count") else len(users)} user(s)...\n')
        
        for user in users:
            self.stdout.write(f'\n--- User: {user.username} (ID: {user.id}) ---')
            
            # Get profile
            try:
                profile = UserProfile.objects.get(user=user)
                self.stdout.write(f'Profile: paidUser={profile.paidUser}')
            except UserProfile.DoesNotExist:
                self.stdout.write(self.style.WARNING('⚠ No profile found, creating...'))
                profile = UserProfile.objects.create(user=user)
            
            # Count files
            file_count = IDEFile.objects.filter(project__user=user).count()
            self.stdout.write(f'IDE Files: {file_count}')
            
            # Count earlier users (for OG check)
            earlier_users = User.objects.filter(date_joined__lt=user.date_joined).count()
            self.stdout.write(f'User position: #{earlier_users + 1} (joined {user.date_joined})')
            
            # Check current achievements
            current_achievements = UserAchievement.objects.filter(user=user)
            self.stdout.write(f'Current achievements: {current_achievements.count()}')
            for ua in current_achievements:
                self.stdout.write(f'  - {ua.achievement.name} (earned {ua.earned_at})')
            
            # Force re-award if requested
            if options['force']:
                self.stdout.write(self.style.WARNING('Force mode: Removing existing achievements...'))
                current_achievements.delete()
            
            # Check what achievements they should have
            self.stdout.write('\nChecking eligibility:')
            
            # OG User
            if earlier_users < 100:
                result = check_og_user(user)
                if result:
                    self.stdout.write(self.style.SUCCESS('  ✓ Awarded OG User achievement'))
                else:
                    if UserAchievement.objects.filter(user=user, achievement__achievement_type='og_user').exists():
                        self.stdout.write(self.style.SUCCESS('  ✓ Already has OG User achievement'))
                    else:
                        self.stdout.write(self.style.ERROR('  ✗ Failed to award OG User achievement'))
            else:
                self.stdout.write(f'  - Not eligible for OG User (user #{earlier_users + 1})')
            
            # Paid User
            if profile.paidUser:
                result = check_paid_user(user)
                if result:
                    self.stdout.write(self.style.SUCCESS('  ✓ Awarded Paid User achievement'))
                else:
                    if UserAchievement.objects.filter(user=user, achievement__achievement_type='paid_user').exists():
                        self.stdout.write(self.style.SUCCESS('  ✓ Already has Paid User achievement'))
                    else:
                        self.stdout.write(self.style.ERROR('  ✗ Failed to award Paid User achievement'))
            else:
                self.stdout.write('  - Not eligible for Paid User (not a paid user)')
            
            # Beginner
            if file_count >= 1:
                result = check_beginner(user)
                if result:
                    self.stdout.write(self.style.SUCCESS('  ✓ Awarded Beginner achievement'))
                else:
                    if UserAchievement.objects.filter(user=user, achievement__achievement_type='beginner').exists():
                        self.stdout.write(self.style.SUCCESS('  ✓ Already has Beginner achievement'))
                    else:
                        self.stdout.write(self.style.ERROR('  ✗ Failed to award Beginner achievement'))
            else:
                self.stdout.write('  - Not eligible for Beginner (no files created)')
            
            # Final count
            final_achievements = UserAchievement.objects.filter(user=user)
            self.stdout.write(f'\nFinal achievement count: {final_achievements.count()}')
        
        self.stdout.write(self.style.SUCCESS('\n=== DONE ===\n'))
