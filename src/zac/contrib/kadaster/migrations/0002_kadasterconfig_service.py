# Generated by Django 2.2.16 on 2020-11-03 08:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("zgw_consumers", "0011_remove_service_extra"),
        ("kadaster", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="kadasterconfig",
            name="service",
            field=models.ForeignKey(
                help_text="Configuration for the service that makes requests to the BAG API.",
                limit_choices_to={"api_type": "orc"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="zgw_consumers.Service",
                verbose_name="service",
            ),
        ),
    ]
