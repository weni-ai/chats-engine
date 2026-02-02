from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0026_alter_room_closed_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='last_message_media',
            field=models.JSONField(blank=True, default=list, verbose_name='Last message media'),
        ),
    ]
