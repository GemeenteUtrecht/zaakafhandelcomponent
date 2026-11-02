from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_coreconfig_read_only_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="coreconfig",
            name="decommissioned_mode",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "If enabled, every logged-in user except superusers only sees a "
                    "page stating that the ZAC has been decommissioned. Application "
                    "tokens and notifications keep working. See "
                    "zac.core.middleware.DecommissionedModeMiddleware."
                ),
                verbose_name="Decommissioned mode",
            ),
        ),
    ]
