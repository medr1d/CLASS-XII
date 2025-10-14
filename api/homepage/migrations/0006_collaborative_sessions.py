# Generated migration for collaborative session features

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('homepage', '0005_add_new_features'),
    ]

    operations = [
        migrations.AddField(
            model_name='sharedcode',
            name='session_type',
            field=models.CharField(
                choices=[('simple', 'Simple Share (Read-only)'), ('collaborative', 'Collaborative Session (Real-time editing)')],
                default='simple',
                max_length=20
            ),
        ),
        migrations.AddField(
            model_name='sharedcode',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='sharedcode',
            name='imported_files',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='sharedcode',
            name='session_state',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.CreateModel(
            name='SessionMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('permission', models.CharField(choices=[('view', 'View Only'), ('edit', 'Can Edit')], default='view', max_length=10)),
                ('is_online', models.BooleanField(default=False)),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('last_active', models.DateTimeField(auto_now=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='session_members', to='homepage.sharedcode')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='session_memberships', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='sharedcode',
            name='members',
            field=models.ManyToManyField(related_name='collaborative_sessions', through='homepage.SessionMember', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddIndex(
            model_name='sharedcode',
            index=models.Index(fields=['session_type', 'is_active'], name='homepage_sh_session_idx'),
        ),
        migrations.AddIndex(
            model_name='sessionmember',
            index=models.Index(fields=['session', 'is_online'], name='homepage_se_session_online_idx'),
        ),
        migrations.AddIndex(
            model_name='sessionmember',
            index=models.Index(fields=['user', '-last_active'], name='homepage_se_user_active_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='sessionmember',
            unique_together={('session', 'user')},
        ),
    ]
