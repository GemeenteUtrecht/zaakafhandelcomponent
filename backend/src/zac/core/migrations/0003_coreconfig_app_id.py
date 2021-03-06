# Generated by Django 2.2.16 on 2021-02-09 09:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_auto_20200922_1534"),
    ]

    operations = [
        migrations.AddField(
            model_name="coreconfig",
            name="app_id",
            field=models.URLField(
                default="",
                help_text="A (globally) unique ID of the BPTL application. In this case the URL that points to the appropriateapplication on the Openzaak Autorisaties API.",
                verbose_name="BPTL Application ID",
            ),
        ),
    ]
