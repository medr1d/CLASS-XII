"""
Management command to clean up expired collaborative sessions.
Run this command periodically (e.g., via cron) to mark expired sessions as inactive.

Usage:
    python manage.py cleanup_sessions
    
Cron example (runs daily at 2 AM):
    0 2 * * * cd /path/to/project && python manage.py cleanup_sessions
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from homepage.models import SharedCode, SessionMember


class Command(BaseCommand):
    help = 'Clean up expired collaborative coding sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about cleaned sessions',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        now = timezone.now()
        
        # Find expired collaborative sessions
        expired_sessions = SharedCode.objects.filter(
            session_type='collaborative',
            is_active=True,
            expires_at__lt=now
        )
        
        count = expired_sessions.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No expired sessions found.'))
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'[DRY RUN] Would clean up {count} expired session(s):')
            )
            if verbose:
                for session in expired_sessions:
                    age_days = (now - session.created_at).days
                    self.stdout.write(
                        f'  - {session.title} (ID: {session.share_id}, Age: {age_days} days, '
                        f'Expired: {session.expires_at.strftime("%Y-%m-%d %H:%M")})'
                    )
        else:
            if verbose:
                self.stdout.write(f'Cleaning up {count} expired session(s):')
                for session in expired_sessions:
                    age_days = (now - session.created_at).days
                    self.stdout.write(
                        f'  - {session.title} (ID: {session.share_id}, Age: {age_days} days)'
                    )
            
            # Mark sessions as inactive
            updated = expired_sessions.update(is_active=False)
            
            # Optional: Mark all session members as offline
            member_count = SessionMember.objects.filter(
                session__in=expired_sessions
            ).update(is_online=False)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully cleaned up {updated} expired session(s) '
                    f'and updated {member_count} member record(s).'
                )
            )
        
        # Show statistics
        if verbose:
            active_sessions = SharedCode.objects.filter(
                session_type='collaborative',
                is_active=True
            ).count()
            
            total_sessions = SharedCode.objects.filter(
                session_type='collaborative'
            ).count()
            
            self.stdout.write('\nSession Statistics:')
            self.stdout.write(f'  Active sessions: {active_sessions}')
            self.stdout.write(f'  Total sessions: {total_sessions}')
            self.stdout.write(f'  Inactive sessions: {total_sessions - active_sessions}')
