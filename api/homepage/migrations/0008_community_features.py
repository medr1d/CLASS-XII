# Generated migration for community features

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('homepage', '0007_add_last_activity'),
    ]

    operations = [
        migrations.CreateModel(
            name='Friendship',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected'), ('blocked', 'Blocked')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('from_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_friend_requests', to=settings.AUTH_USER_MODEL)),
                ('to_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_friend_requests', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='DirectMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_messages', to=settings.AUTH_USER_MODEL)),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='UserStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_online', models.BooleanField(default=False)),
                ('last_seen', models.DateTimeField(default=django.utils.timezone.now)),
                ('status_message', models.CharField(blank=True, default='', max_length=100)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='online_status', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'User statuses',
            },
        ),
        migrations.AddIndex(
            model_name='friendship',
            index=models.Index(fields=['from_user', 'status'], name='homepage_fr_from_us_9f5b15_idx'),
        ),
        migrations.AddIndex(
            model_name='friendship',
            index=models.Index(fields=['to_user', 'status'], name='homepage_fr_to_user_a7c8e6_idx'),
        ),
        migrations.AddIndex(
            model_name='friendship',
            index=models.Index(fields=['-created_at'], name='homepage_fr_created_4d92f1_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='friendship',
            unique_together={('from_user', 'to_user')},
        ),
        migrations.AddIndex(
            model_name='directmessage',
            index=models.Index(fields=['sender', 'recipient', '-created_at'], name='homepage_di_sender__7a8b9c_idx'),
        ),
        migrations.AddIndex(
            model_name='directmessage',
            index=models.Index(fields=['recipient', 'is_read'], name='homepage_di_recipie_1e2f3g_idx'),
        ),
        migrations.AddIndex(
            model_name='directmessage',
            index=models.Index(fields=['-created_at'], name='homepage_di_created_5h6i7j_idx'),
        ),
        migrations.AddIndex(
            model_name='userstatus',
            index=models.Index(fields=['is_online', '-last_seen'], name='homepage_us_is_onli_8k9l0m_idx'),
        ),
    ]
