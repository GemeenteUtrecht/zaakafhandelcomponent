from django.db import migrations, models


def deduplicate_atomic_permissions(apps, _):
    AtomicPermission = apps.get_model("accounts", "AtomicPermission")
    UserAtomicPermission = apps.get_model("accounts", "UserAtomicPermission")

    duplicated_groups = (
        AtomicPermission.objects.values("permission", "object_url")
        .annotate(count=models.Count("id"), min_id=models.Min("id"))
        .filter(count__gt=1)
    )
    for group in duplicated_groups:
        duplicated_permissions = AtomicPermission.objects.filter(
            permission=group["permission"], object_url=group["object_url"]
        ).exclude(id=group["min_id"])
        first_permission = AtomicPermission.objects.get(id=group["min_id"])
        # change FK for UserAtomicPermission
        UserAtomicPermission.objects.filter(
            atomic_permission__in=duplicated_permissions
        ).update(atomic_permission=first_permission)
        duplicated_permissions.delete()


class Migration(migrations.Migration):

    dependencies = [("accounts", "0039_auto_20210625_1028")]

    operations = [
        migrations.RunPython(deduplicate_atomic_permissions, migrations.RunPython.noop)
    ]
