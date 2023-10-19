# Generated by Django 3.2.12 on 2023-09-05 06:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0030_auto_20230905_0557"),
    ]

    operations = [
        migrations.AlterField(
            model_name="authorizationprofile",
            name="name",
            field=models.CharField(
                help_text="Use an easily recognizable name that maps to the function of users that's unique.",
                max_length=255,
                unique=True,
                verbose_name="name",
            ),
        ),
        migrations.AddField(
            model_name="blueprintpermission",
            name="hashkey",
            field=models.CharField(blank=True, max_length=32, null=True, unique=True),
        ),
        migrations.AlterUniqueTogether(
            name="blueprintpermission",
            unique_together={("role", "policy", "object_type")},
        ),
    ]
