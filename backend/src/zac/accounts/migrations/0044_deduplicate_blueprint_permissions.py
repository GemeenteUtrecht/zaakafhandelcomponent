from django.db import migrations, models


def deduplicate_blueprint_permissions(apps, _):
    BlueprintPermission = apps.get_model("accounts", "BlueprintPermission")
    AuthorizationProfile = apps.get_model("accounts", "AuthorizationProfile")

    duplicated_groups = (
        BlueprintPermission.objects.values("permission", "policy")
        .annotate(count=models.Count("id"), min_id=models.Min("id"))
        .filter(count__gt=1)
        .distinct()
    )

    for group in duplicated_groups:
        duplicated_permissions = BlueprintPermission.objects.filter(
            permission=group["permission"], policy=group["policy"]
        ).exclude(id=group["min_id"])
        first_permission = BlueprintPermission.objects.get(id=group["min_id"])

        # change M2M for AuthorizationProfile
        for permission in duplicated_permissions:
            auth_profiles = AuthorizationProfile.objects.filter(
                blueprint_permissions=permission
            ).distinct()
            for auth_profile in auth_profiles:
                auth_profile.blueprint_permissions.remove(permission)
                auth_profile.blueprint_permissions.add(first_permission)

        duplicated_permissions.delete()


class Migration(migrations.Migration):

    dependencies = [("accounts", "0043_auto_20210701_1528")]

    operations = [
        migrations.RunPython(
            deduplicate_blueprint_permissions, migrations.RunPython.noop
        )
    ]
