# Generated by Django 4.0.5 on 2022-08-25 04:33

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('quickmessages', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='quickmessage',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, to_field='email', verbose_name='quick_messages'),
        ),
    ]
