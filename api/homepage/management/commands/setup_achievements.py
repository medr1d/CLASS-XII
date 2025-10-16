"""
Management command to setup achievements system and award achievements to existing users
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from homepage.achievements import create_default_achievements, initialize_user_achievements


class Command(BaseCommand):
    help = 'Setup achievements system and award achievements to existing users'

    def handle(self, *args, **options):
        self.stdout.write('Creating default achievements...')
        create_default_achievements()
        self.stdout.write(self.style.SUCCESS('✓ Default achievements created'))
        
        self.stdout.write('\nChecking achievements for existing users...')
        users = User.objects.all()
        
        for user in users:
            self.stdout.write(f'  Checking user: {user.username}')
            initialize_user_achievements(user)
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Checked achievements for {users.count()} users'))
        self.stdout.write(self.style.SUCCESS('Achievement system setup complete!'))
