# Generated by Django 3.2.12 on 2024-03-13 13:47

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Board",
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
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        help_text="Unique identifier (UUID4)",
                        unique=True,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Name of the board",
                        max_length=50,
                        verbose_name="name",
                    ),
                ),
                (
                    "slug",
                    models.SlugField(
                        help_text="Slug of the board",
                        max_length=100,
                        unique=True,
                        verbose_name="slug",
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Date-time when the board was created",
                        verbose_name="created",
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Date-time when the board was modified last time",
                        verbose_name="modified",
                    ),
                ),
            ],
            options={
                "verbose_name": "board",
                "verbose_name_plural": "boards",
            },
        ),
        migrations.CreateModel(
            name="BoardColumn",
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
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        help_text="Unique identifier (UUID4)",
                        unique=True,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Name of the board column",
                        max_length=50,
                        verbose_name="name",
                    ),
                ),
                (
                    "slug",
                    models.SlugField(
                        help_text="Slug of the board column",
                        max_length=100,
                        verbose_name="slug",
                    ),
                ),
                (
                    "order",
                    models.PositiveSmallIntegerField(
                        help_text="Order of the column", verbose_name="order"
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Date-time when the column was created",
                        verbose_name="created",
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Date-time when the column was modified last time",
                        verbose_name="modified",
                    ),
                ),
                (
                    "board",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="columns",
                        to="board.board",
                    ),
                ),
            ],
            options={
                "verbose_name": "board column",
                "verbose_name_plural": "board columns",
                "ordering": ("board", "order", "slug"),
                "unique_together": {("board", "slug")},
            },
        ),
        migrations.CreateModel(
            name="BoardItem",
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
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        help_text="Unique identifier (UUID4)",
                        unique=True,
                    ),
                ),
                (
                    "object_type",
                    models.CharField(
                        choices=[("zaak", "zaak")],
                        default="zaak",
                        help_text="Type of the board item",
                        max_length=50,
                        verbose_name="object type",
                    ),
                ),
                (
                    "object",
                    models.URLField(
                        db_index=True,
                        help_text="URL-reference of the OBJECT in one of ZGW APIs this board item relates to",
                        verbose_name="object",
                    ),
                ),
                (
                    "column",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="board.boardcolumn",
                    ),
                ),
            ],
            options={
                "verbose_name": "board item",
                "verbose_name_plural": "board items",
            },
        ),
    ]