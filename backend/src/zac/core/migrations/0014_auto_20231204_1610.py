# Generated by Django 3.2.12 on 2023-12-04 16:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_metaobjecttypesconfig_oudbehandelaren_objecttype"),
    ]

    operations = [
        migrations.AddField(
            model_name="metaobjecttypesconfig",
            name="review_objecttype",
            field=models.URLField(
                default="",
                help_text="URL-reference to the review OBJECTTYPE. This is used to register an advice/approval to a review request.",
                verbose_name="URL-reference to review in OBJECTTYPES API.",
            ),
        ),
        migrations.AddField(
            model_name="metaobjecttypesconfig",
            name="review_request_objecttype",
            field=models.URLField(
                default="",
                help_text="URL-reference to the review request OBJECTTYPE. This is used to register a review request.",
                verbose_name="URL-reference to review request in OBJECTTYPES API.",
            ),
        ),
    ]
