# Generated by Django 3.2.12 on 2024-03-29 14:36

from django.db import migrations


def create_uniquely_active_userauthprofiles(apps, schema_editor):
    UserAuthorizationProfile = apps.get_model("accounts", "UserAuthorizationProfile")
    User = apps.get_model("accounts", "User")
    AuthorizationProfile = apps.get_model("accounts", "AuthorizationProfile")

    for user in User.objects.all():
        for ap in AuthorizationProfile.objects.all():
            qs = UserAuthorizationProfile.objects.filter(
                user=user, auth_profile=ap
            ).order_by("-id")
            if qs.exists():
                i = 0
                for i, uap in enumerate(list(qs)):
                    if i == 0:
                        uap.is_active = True
                    else:
                        uap.is_active = False
                    uap.save()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_userauthorizationprofile_is_active"),
    ]

    operations = [migrations.RunPython(create_uniquely_active_userauthprofiles)]
