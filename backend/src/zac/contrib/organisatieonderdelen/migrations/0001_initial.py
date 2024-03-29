# Generated by Django 3.2.12 on 2024-03-13 13:47

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="OrganisatieOnderdeel",
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
                ("name", models.CharField(max_length=100, verbose_name="name")),
                (
                    "slug",
                    models.SlugField(max_length=24, unique=True, verbose_name="slug"),
                ),
            ],
            options={
                "verbose_name": "organisatie-onderdeel",
                "verbose_name_plural": "organisatie-onderdelen",
            },
        ),
    ]
