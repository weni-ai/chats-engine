# Generated by Django 4.0.5 on 2022-08-22 14:03

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='QuickMessage',
            fields=[
                ('uuid', models.UUIDField(default=uuid.uuid4, primary_key=True, serialize=False)),
                ('created_on', models.DateTimeField(auto_now_add=True, verbose_name='Created on')),
                ('modified_on', models.DateTimeField(auto_now=True, verbose_name='Modified on')),
                ('shortcut', models.CharField(max_length=50, verbose_name='shortcut')),
                ('text', models.TextField(verbose_name='text')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='quick_messages')),
            ],
            options={
                'verbose_name': 'Quick Message',
                'verbose_name_plural': 'Quick Messages',
            },
        ),
    ]
