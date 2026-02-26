# Generated migration for retry_count field and status choices

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0007_alter_roommetrics_first_response_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportstatus',
            name='retry_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='reportstatus',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('ready', 'Ready'),
                    ('in_progress', 'In Progress'),
                    ('failed', 'Failed'),
                    ('permanently_failed', 'Permanently Failed'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
    ]
