# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import os
import django
from pathlib import Path

# Get Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mywebsite.settings')
django.setup()

from django.conf import settings

# Collect all template files
template_files = []
for template_dir in ['auth_app/templates', 'homepage/templates']:
    if os.path.exists(template_dir):
        for root, dirs, files in os.walk(template_dir):
            for file in files:
                if file.endswith('.html'):
                    src = os.path.join(root, file)
                    dst = root
                    template_files.append((src, dst))

# Collect all static files
static_files = []
for static_dir in ['auth_app/static', 'homepage/static', 'static']:
    if os.path.exists(static_dir):
        for root, dirs, files in os.walk(static_dir):
            for file in files:
                src = os.path.join(root, file)
                dst = root
                static_files.append((src, dst))

# Include database
database_files = []
if os.path.exists('db.sqlite3'):
    database_files.append(('db.sqlite3', '.'))

a = Analysis(
    ['run_server.py'],
    pathex=[],
    binaries=[],
    datas=template_files + static_files + database_files,
    hiddenimports=[
        'django',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django.contrib.sitemaps',
        'django.core.management',
        'django.core.management.commands.runserver',
        'django.core.management.commands.migrate',
        'django.template',
        'django.template.loaders',
        'django.template.loaders.filesystem',
        'django.template.loaders.app_directories',
        'mywebsite',
        'mywebsite.settings',
        'mywebsite.urls',
        'mywebsite.wsgi',
        'auth_app',
        'auth_app.models',
        'auth_app.views',
        'auth_app.urls',
        'homepage',
        'homepage.models',
        'homepage.views',
        'homepage.urls',
        'homepage.sitemaps',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DjangoWebsite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # You can add an .ico file path here if you want
)
