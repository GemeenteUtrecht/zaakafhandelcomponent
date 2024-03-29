# Generated by Django 3.2.12 on 2024-03-13 13:47

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="KillableTask",
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
                    "name",
                    models.CharField(
                        max_length=100, unique=True, verbose_name="task name"
                    ),
                ),
            ],
            options={
                "verbose_name": "camunda task",
                "verbose_name_plural": "camunda tasks",
            },
        ),
    ]
