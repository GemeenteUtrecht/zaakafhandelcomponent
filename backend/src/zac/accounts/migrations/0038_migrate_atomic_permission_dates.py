from django.db import migrations, models


def migrate_atomic_permission_dates(apps, _):
    UserAtomicPermission = apps.get_model("accounts", "UserAtomicPermission")
    UserAtomicPermission.objects.update(
        start_date=models.Subquery(
            UserAtomicPermission.objects.filter(id=models.OuterRef("id")).values(
                "atomic_permission__start_date"
            )[:1]
        ),
        end_date=models.Subquery(
            UserAtomicPermission.objects.filter(id=models.OuterRef("id")).values(
                "atomic_permission__end_date"
            )[:1]
        ),
    )


class Migration(migrations.Migration):

    dependencies = [("accounts", "0037_auto_20210625_1005")]

    operations = [
        migrations.RunPython(migrate_atomic_permission_dates, migrations.RunPython.noop)
    ]
