# Generated by Django 2.2.16 on 2021-03-19 11:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0025_migrate_to_permission_definitions"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="authorizationprofile",
            name="oo",
        ),
        migrations.RemoveField(
            model_name="authorizationprofile",
            name="permission_sets",
        ),
        migrations.DeleteModel(
            name="InformatieobjecttypePermission",
        ),
        migrations.DeleteModel(
            name="PermissionSet",
        ),
    ]
