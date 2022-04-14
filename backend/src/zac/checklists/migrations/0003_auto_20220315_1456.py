# Generated by Django 2.2.27 on 2022-03-15 14:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("checklists", "0002_auto_20220315_1450"),
    ]

    operations = [
        migrations.AlterField(
            model_name="checklist",
            name="zaak",
            field=models.URLField(
                help_text="URL-reference to the ZAAK in its API.",
                max_length=1000,
                unique=True,
                verbose_name="ZAAK-URL",
            ),
        ),
    ]