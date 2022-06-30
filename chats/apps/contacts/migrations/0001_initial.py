# Generated by Django 4.0.5 on 2022-06-23 15:37

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_on', models.DateTimeField(auto_now_add=True, verbose_name='Created on')),
                ('modified_on', models.DateTimeField(auto_now=True, verbose_name='Modified on')),
                ('name', models.CharField(blank=True, max_length=30, verbose_name='first name')),
                ('email', models.EmailField(help_text='User email', max_length=254, unique=True, verbose_name='email')),
            ],
            options={
                'verbose_name': 'Contact',
                'verbose_name_plural': 'Contacts',
            },
        ),
    ]
