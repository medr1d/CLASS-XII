"""
Management command to initialize default achievements
"""
from django.core.management.base import BaseCommand
from homepage.achievements import create_default_achievements


class Command(BaseCommand):
    help = 'Initialize default achievements in the database'

    def handle(self, *args, **options):
        self.stdout.write('Creating default achievements...')
        create_default_achievements()
        self.stdout.write(self.style.SUCCESS('Successfully created default achievements!'))
