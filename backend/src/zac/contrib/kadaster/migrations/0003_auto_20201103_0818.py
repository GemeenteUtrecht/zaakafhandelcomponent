# Generated by Django 2.2.16 on 2020-11-03 08:18
from django.db import migrations

from zgw_consumers.constants import APITypes, AuthTypes


def refactor_configuration_forward(apps, schema_editor):
    Service = apps.get_model("zgw_consumers", "Service")
    KadasterConfig = apps.get_model("kadaster", "KadasterConfig")
    configuration = KadasterConfig.objects.first()
    if configuration is None:
        return
    configuration.service = Service.objects.create(
        label="Kadaster",
        api_type=APITypes.orc,
        api_root=configuration.bag_api,
        auth_type=AuthTypes.api_key,
        header_key="X-Api-Key",
        header_value=configuration.api_key,
    )
    configuration.save()


def refactor_configuration_backwards(apps, schema_editor):
    KadasterConfig = apps.get_model("kadaster", "KadasterConfig")
    configuration = KadasterConfig.objects.first()
    if configuration is None:
        return

    configuration.bag_api = configuration.service.api_root
    configuration.api_key = configuration.service.header_value
    configuration.save()


class Migration(migrations.Migration):

    dependencies = [
        ("zgw_consumers", "0011_remove_service_extra"),
        ("kadaster", "0002_kadasterconfig_service"),
    ]

    operations = [
        migrations.RunPython(
            refactor_configuration_forward, refactor_configuration_backwards
        )
    ]
