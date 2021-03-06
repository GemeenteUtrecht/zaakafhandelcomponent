# Generated by Django 2.2.16 on 2020-10-05 10:44

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_auto_20200925_1038"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="permissionset",
            name="informatieobjecttype_omschrijving",
        ),
        migrations.RemoveField(
            model_name="permissionset",
            name="informatieobjecttype_va",
        ),
        migrations.AddField(
            model_name="permissionset",
            name="informatieobjecttype_max_va",
            field=models.CharField(
                choices=[
                    ("openbaar", "Openbaar"),
                    ("beperkt_openbaar", "Beperkt openbaar"),
                    ("intern", "Intern"),
                    ("zaakvertrouwelijk", "Zaakvertrouwelijk"),
                    ("vertrouwelijk", "Vertrouwelijk"),
                    ("confidentieel", "Confidentieel"),
                    ("geheim", "Geheim"),
                    ("zeer_geheim", "Zeer geheim"),
                ],
                default="openbaar",
                help_text="Maximum level of confidentiality for the document types in the case.",
                max_length=100,
                verbose_name="informatieobjecttype maximum vertrouwelijkheidaanduiding",
            ),
        ),
        migrations.AddField(
            model_name="permissionset",
            name="informatieobjecttype_omschrijvingen",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=100),
                blank=True,
                default=list,
                help_text="Specifies which document types within the case can be viewed. If left empty, all documents in the case can be viewed.",
                size=None,
                verbose_name="informatieobjecttype omschrijvingen",
            ),
        ),
    ]
