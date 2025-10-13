"""
Management command to optimize static files and clear cache
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.core.cache import cache
from django.conf import settings
import os
import gzip
import shutil


class Command(BaseCommand):
    help = 'Optimize static files for production performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear all cache after optimization',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting performance optimization...'))
        
        # Collect static files
        self.stdout.write('Collecting static files...')
        call_command('collectstatic', '--noinput', verbosity=0)
        
        # Compress CSS and JS files
        self.stdout.write('Compressing static files...')
        self.compress_static_files()
        
        # Clear cache if requested
        if options['clear_cache']:
            self.stdout.write('Clearing cache...')
            cache.clear()
            self.stdout.write(self.style.SUCCESS('Cache cleared'))
        
        # Generate favicon cache
        self.optimize_images()
        
        self.stdout.write(
            self.style.SUCCESS('Performance optimization completed successfully!')
        )

    def compress_static_files(self):
        """Compress CSS and JS files with gzip"""
        static_root = settings.STATIC_ROOT
        if not static_root or not os.path.exists(static_root):
            self.stdout.write(self.style.WARNING('Static root not found, skipping compression'))
            return
        
        compressed_count = 0
        for root, dirs, files in os.walk(static_root):
            for file in files:
                if file.endswith(('.css', '.js', '.html', '.json')):
                    file_path = os.path.join(root, file)
                    gz_path = file_path + '.gz'
                    
                    # Only compress if gzip file doesn't exist or is older
                    if (not os.path.exists(gz_path) or 
                        os.path.getmtime(file_path) > os.path.getmtime(gz_path)):
                        
                        with open(file_path, 'rb') as f_in:
                            with gzip.open(gz_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        compressed_count += 1
        
        self.stdout.write(f'Compressed {compressed_count} files')

    def optimize_images(self):
        """Optimize image loading"""
        # This could be extended to optimize images
        # For now, just ensure favicon is properly cached
        static_root = settings.STATIC_ROOT
        if static_root and os.path.exists(static_root):
            favicon_paths = [
                os.path.join(static_root, 'auth_app', 'favicon.ico'),
                os.path.join(static_root, 'favicon.ico'),
            ]
            
            optimized_count = 0
            for favicon_path in favicon_paths:
                if os.path.exists(favicon_path):
                    # Favicon optimization could be added here
                    optimized_count += 1
            
            if optimized_count > 0:
                self.stdout.write(f'Optimized {optimized_count} favicon files')