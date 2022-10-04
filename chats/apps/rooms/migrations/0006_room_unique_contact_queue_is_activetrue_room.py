# Generated by Django 4.0.5 on 2022-10-01 01:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0005_alter_room_user'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='room',
            constraint=models.UniqueConstraint(condition=models.Q(('is_active', True)), fields=('contact', 'queue'), name='unique_contact_queue_is_activetrue_room'),
        ),
    ]