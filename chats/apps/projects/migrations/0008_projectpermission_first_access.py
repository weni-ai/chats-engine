# Generated by Django 4.0.5 on 2022-09-27 17:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0007_projectpermission_unique_user_permission'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectpermission',
            name='first_access',
            field=models.BooleanField(default=True, verbose_name='Its the first access of user?'),
        ),
    ]
