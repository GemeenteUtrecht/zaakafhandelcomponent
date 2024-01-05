# Generated by Django 3.2.12 on 2024-01-06 20:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_metaobjecttypesconfig_meta_list_objecttype"),
    ]

    operations = [
        migrations.AddField(
            model_name="metaobjecttypesconfig",
            name="default",
            field=models.BooleanField(
                default=True,
                help_text="Setting to False will allow the user to define custom objecttypes instead of the URL-references retrieved from the list of meta objecttypes from the OBJECTS API.",
            ),
        ),
    ]
