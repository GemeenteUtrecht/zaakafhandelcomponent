# Generated by Django 2.2.12 on 2020-06-11 07:39

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("zgw_consumers", "0009_auto_20200401_0829"),
    ]

    operations = [
        migrations.CreateModel(
            name="KownslConfig",
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
                    "service",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="zgw_consumers.Service",
                    ),
                ),
            ],
            options={
                "verbose_name": "Kownsl configuration",
            },
        ),
    ]
