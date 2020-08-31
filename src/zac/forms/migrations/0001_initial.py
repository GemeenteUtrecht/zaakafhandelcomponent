# Generated by Django 2.2.5 on 2020-04-23 13:26

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("zgw_consumers", "0009_auto_20200401_0829"),
    ]

    operations = [
        migrations.CreateModel(
            name="FormsConfig",
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
                    "forms_service",
                    models.ForeignKey(
                        blank=True,
                        help_text="Select the service definition where Open Forms is hosted.",
                        limit_choices_to={"api_type": "orc"},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="zgw_consumers.Service",
                    ),
                ),
            ],
            options={
                "verbose_name": "formulierenconfiguratie",
            },
        ),
    ]
