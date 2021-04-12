from django.db import migrations


def migrate_to_blueprint_permissions(apps, _):
    PermissionDefinition = apps.get_model("accounts", "PermissionDefinition")
    BlueprintPermission = apps.get_model("accounts", "BlueprintPermission")

    # migrate blueprint permission definitions
    for permission_definition in PermissionDefinition.objects.exclude(policy={}):
        blueprint_permission = BlueprintPermission.objects.create(
            permission=permission_definition.permission,
            object_type=permission_definition.object_type,
            policy=permission_definition.policy,
            start_date=permission_definition.start_date,
            end_date=permission_definition.end_date,
        )
        # add to auth profiles
        for auth_profile in permission_definition.auth_profiles.all():
            auth_profile.blueprint_permissions.add(blueprint_permission)

        permission_definition.delete()


def migrate_from_blueprint_permissions(apps, _):
    PermissionDefinition = apps.get_model("accounts", "PermissionDefinition")
    BlueprintPermission = apps.get_model("accounts", "BlueprintPermission")

    for blueprint_permission in BlueprintPermission.objects.all():
        permission_definition = PermissionDefinition.objects.create(
            permission=blueprint_permission.permission,
            object_type=blueprint_permission.object_type,
            policy=blueprint_permission.policy,
            start_date=blueprint_permission.start_date,
            end_date=blueprint_permission.end_date,
        )
        for auth_profile in blueprint_permission.auth_profiles.all():
            auth_profile.permission_definitions.add(permission_definition)

        BlueprintPermission.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0027_auto_20210325_1633"),
        ("zgw_consumers", "0012_auto_20210104_1039"),
    ]

    operations = [
        migrations.RunPython(
            migrate_to_blueprint_permissions, migrate_from_blueprint_permissions
        ),
    ]
