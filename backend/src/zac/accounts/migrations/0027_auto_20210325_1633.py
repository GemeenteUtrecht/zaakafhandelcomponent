# Generated by Django 2.2.16 on 2021-03-25 16:33

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0026_auto_20210319_1158"),
    ]

    operations = [
        migrations.CreateModel(
            name="BlueprintPermission",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "object_type",
                    models.CharField(
                        choices=[("zaak", "zaak"), ("document", "document")],
                        help_text="Type of the objects this permission applies to",
                        max_length=50,
                        verbose_name="object type",
                    ),
                ),
                (
                    "permission",
                    models.CharField(
                        help_text="Name of the permission",
                        max_length=255,
                        verbose_name="Permission",
                    ),
                ),
                (
                    "policy",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        help_text="Blueprint permission definitions, used to check the access to objects based on their properties i.e. zaaktype, informatieobjecttype",
                        verbose_name="policy",
                    ),
                ),
                (
                    "start_date",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        help_text="Start date of the permission",
                        verbose_name="start date",
                    ),
                ),
                (
                    "end_date",
                    models.DateTimeField(
                        blank=True,
                        help_text="End date of the permission",
                        null=True,
                        verbose_name="end date",
                    ),
                ),
            ],
            options={
                "verbose_name": "blueprint definition",
                "verbose_name_plural": "blueprint definitions",
            },
        ),
        migrations.AddField(
            model_name="authorizationprofile",
            name="blueprint_permissions",
            field=models.ManyToManyField(
                related_name="auth_profiles",
                to="accounts.BlueprintPermission",
                verbose_name="blueprint permissions",
            ),
        ),
    ]
