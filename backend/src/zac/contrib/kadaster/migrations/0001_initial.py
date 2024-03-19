# Generated by Django 3.2.12 on 2024-03-13 13:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("zgw_consumers", "0016_auto_20220818_1412"),
    ]

    operations = [
        migrations.CreateModel(
            name="KadasterConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "locatieserver",
                    models.URLField(
                        default="https://geodata.nationaalgeoregister.nl/locatieserver/v3/",
                        verbose_name="root URL locatieserver",
                    ),
                ),
                (
                    "service",
                    models.ForeignKey(
                        help_text="Configuration for the service that makes requests to the BAG API.",
                        limit_choices_to={"api_type": "orc"},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="zgw_consumers.service",
                        verbose_name="service",
                    ),
                ),
            ],
            options={
                "verbose_name": "kadasterconfiguratie",
            },
        ),
    ]