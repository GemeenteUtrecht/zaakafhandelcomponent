# Generated by Django 3.2.12 on 2022-05-26 12:58

from django.db import migrations


def remove_zaken_request_access_in_atomic_permissions(apps, _):
    AtomicPermission = apps.get_model("accounts", "AtomicPermission")

    for ap in AtomicPermission.objects.filter(permission="zaken:toegang-aanvragen"):
        ap.delete()


def remove_zaken_request_access_in_roles(apps, _):
    Role = apps.get_model("accounts", "Role")

    for role in Role.objects.filter(permissions__contains=["zaken:toegang-aanvragen"]):
        permissions = role.permissions
        permissions.remove("zaken:toegang-aanvragen")
        role.permissions = permissions
        if not role.permissions:
            role.delete()
        else:
            role.save()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0016_auto_20220320_2143"),
    ]

    operations = [
        migrations.RunPython(
            remove_zaken_request_access_in_atomic_permissions, migrations.RunPython.noop
        ),
        migrations.RunPython(
            remove_zaken_request_access_in_roles, migrations.RunPython.noop
        ),
    ]