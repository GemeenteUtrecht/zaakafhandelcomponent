# Generated by Django 3.2.12 on 2022-06-08 06:26

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0018_auto_20220608_0626"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="accessrequest",
            name="user_atomic_permission",
        ),
    ]