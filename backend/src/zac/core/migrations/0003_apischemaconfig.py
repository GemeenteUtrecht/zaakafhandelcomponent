# Generated by Django 3.2.12 on 2025-05-28 12:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_warningbanner"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApiSchemaConfig",
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
                    "client_ztiot_operation_id",
                    models.CharField(
                        default="zaaktypeinformatieobjecttype",
                        help_text="The operation ID to use for the client API schema. This is used to generate the client code for the API schema.",
                        max_length=100,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
