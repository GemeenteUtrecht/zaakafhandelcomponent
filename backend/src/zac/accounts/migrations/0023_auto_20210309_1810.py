# Generated by Django 2.2.16 on 2021-03-09 18:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0022_permissiondefinition"),
    ]

    operations = [
        migrations.AddField(
            model_name="authorizationprofile",
            name="permission_definitions",
            field=models.ManyToManyField(
                related_name="auth_profiles",
                to="accounts.PermissionDefinition",
                verbose_name="permission definitions",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="permission_definitions",
            field=models.ManyToManyField(
                related_name="users",
                to="accounts.PermissionDefinition",
                verbose_name="permission definitions",
            ),
        ),
    ]
