import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .constants import BoardObjectTypes


class Board(models.Model):
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text=_("Unique identifier (UUID4)")
    )
    name = models.CharField(_("name"), max_length=50, help_text=_("Name of the board"))
    slug = models.SlugField(
        _("slug"), max_length=100, unique=True, help_text=_("Slug of the board")
    )
    created = models.DateTimeField(
        _("created"),
        auto_now_add=True,
        help_text=_("Date-time when the board was created"),
    )
    modified = models.DateTimeField(
        _("modified"),
        auto_now=True,
        help_text=_("Date-time when the board was modified last time"),
    )

    class Meta:
        verbose_name = _("board")
        verbose_name_plural = _("boards")

    def __str__(self):
        return self.slug


class BoardColumn(models.Model):
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text=_("Unique identifier (UUID4)")
    )
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="columns")
    name = models.CharField(
        _("name"), max_length=50, help_text=_("Name of the board column")
    )
    slug = models.SlugField(
        _("slug"), max_length=100, help_text=_("Slug of the board column")
    )
    order = models.PositiveSmallIntegerField(
        _("order"), help_text=_("Order of the column")
    )
    created = models.DateTimeField(
        _("created"),
        auto_now_add=True,
        help_text=_("Date-time when the column was created"),
    )
    modified = models.DateTimeField(
        _("modified"),
        auto_now=True,
        help_text=_("Date-time when the column was modified last time"),
    )

    class Meta:
        verbose_name = _("board column")
        verbose_name_plural = _("board columns")
        unique_together = ("board", "slug")

    def __str__(self):
        return f"{self.board}: {self.slug}"


class BoardItem(models.Model):
    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text=_("Unique identifier (UUID4)")
    )
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="items")
    column = models.ForeignKey(
        BoardColumn, on_delete=models.CASCADE, related_name="items"
    )
    object_type = models.CharField(
        _("object type"),
        max_length=50,
        choices=BoardObjectTypes.choices,
        help_text=_("Type of the board item"),
    )
    object = models.URLField(
        _("object"),
        help_text=_("URL of the object in one of ZGW APIs this board item relates to"),
    )

    class Meta:
        verbose_name = _("board item")
        verbose_name_plural = _("board items")
        unique_together = ("board", "object")

    def clean(self):
        if self.board != self.column.board:
            raise ValidationError("Item board should not differ from the column board")
