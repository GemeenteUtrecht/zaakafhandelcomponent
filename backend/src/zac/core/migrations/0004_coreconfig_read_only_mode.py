from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_apischemaconfig"),
    ]

    operations = [
        migrations.AddField(
            model_name="coreconfig",
            name="read_only_mode",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "If enabled, the ZAC API blocks all write requests (POST, PUT, "
                    "PATCH, DELETE) except for a fixed allowlist of endpoints "
                    "required to keep the system usable (e.g. logout, "
                    "account/permission management, and search endpoints that use "
                    "a non-GET method for read-only queries). Users see a warning "
                    "banner while this is active. See "
                    "zac.core.middleware.ReadOnlyModeMiddleware for the allowlist."
                ),
                verbose_name="Read-only mode",
            ),
        ),
    ]
