# Generated migration for new features

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('homepage', '0004_alter_userprofile_theme_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='dark_mode_plots',
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name='ExecutionHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code_snippet', models.TextField()),
                ('output', models.TextField(blank=True)),
                ('error', models.TextField(blank=True)),
                ('execution_time', models.FloatField(default=0)),
                ('filename', models.CharField(default='untitled.py', max_length=255)),
                ('was_successful', models.BooleanField(default=True)),
                ('executed_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='execution_history', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Execution Histories',
                'ordering': ['-executed_at'],
            },
        ),
        migrations.CreateModel(
            name='SharedCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('share_id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ('title', models.CharField(max_length=200)),
                ('code_content', models.TextField()),
                ('description', models.TextField(blank=True)),
                ('language', models.CharField(default='python', max_length=20)),
                ('is_public', models.BooleanField(default=True)),
                ('view_count', models.IntegerField(default=0)),
                ('fork_count', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shared_codes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='executionhistory',
            index=models.Index(fields=['user', '-executed_at'], name='homepage_ex_user_id_9a8c76_idx'),
        ),
        migrations.AddIndex(
            model_name='executionhistory',
            index=models.Index(fields=['user', 'was_successful'], name='homepage_ex_user_id_7e9b45_idx'),
        ),
        migrations.AddIndex(
            model_name='executionhistory',
            index=models.Index(fields=['-executed_at'], name='homepage_ex_execute_3f2a1c_idx'),
        ),
        migrations.AddIndex(
            model_name='sharedcode',
            index=models.Index(fields=['share_id'], name='homepage_sh_share_i_4a5b2e_idx'),
        ),
        migrations.AddIndex(
            model_name='sharedcode',
            index=models.Index(fields=['user', '-created_at'], name='homepage_sh_user_id_6c8d3f_idx'),
        ),
        migrations.AddIndex(
            model_name='sharedcode',
            index=models.Index(fields=['is_public', '-created_at'], name='homepage_sh_is_publ_7d9e4a_idx'),
        ),
        migrations.AddIndex(
            model_name='sharedcode',
            index=models.Index(fields=['-view_count'], name='homepage_sh_view_co_8e0f5b_idx'),
        ),
    ]
