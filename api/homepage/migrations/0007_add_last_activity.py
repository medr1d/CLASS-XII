# Generated migration for adding last_activity tracking

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('homepage', '0006_collaborative_sessions'),
    ]

    operations = [
        migrations.AddField(
            model_name='sharedcode',
            name='last_activity',
            field=models.DateTimeField(default=django.utils.timezone.now, db_index=True),
        ),
    ]
