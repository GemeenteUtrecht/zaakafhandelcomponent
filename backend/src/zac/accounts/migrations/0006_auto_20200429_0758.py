# Generated by Django 2.2.5 on 2020-04-29 07:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_auto_20200406_1018"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Entitlement",
            new_name="AuthorizationProfile",
        ),
        migrations.AlterModelOptions(
            name="authorizationprofile",
            options={
                "verbose_name": "authorization profile",
                "verbose_name_plural": "authorization profiles",
            },
        ),
    ]
