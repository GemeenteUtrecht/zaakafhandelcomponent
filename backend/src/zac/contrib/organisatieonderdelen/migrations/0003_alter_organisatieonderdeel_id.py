# Generated by Django 3.2.12 on 2022-07-10 18:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organisatieonderdelen", "0002_auto_20200923_1400"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organisatieonderdeel",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
    ]