# Generated by Django 3.2.12 on 2024-03-29 08:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="userauthorizationprofile",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="is active"),
        ),
    ]
