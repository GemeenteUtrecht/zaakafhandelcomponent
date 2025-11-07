import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from zac.elasticsearch.api import get_zaak_document

from .constants import BoardObjectTypes
from .query import BoardItemQuerySet


class Board(models.Model):
    """
    A `board`, also referred to as `dashboard`, allows the end user to quickly
    identify statuses of ZAAKen.
    """

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
    """
    A single column of the board. A board can hold multiple columns.
    """

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
        ordering = ("board", "order", "slug")

    def __str__(self):
        return f"{self.board}: {self.slug}"


class BoardItem(models.Model):
    """
    A single board item. A board column can hold multiple board items.
    """

    uuid = models.UUIDField(
        unique=True, default=uuid.uuid4, help_text=_("Unique identifier (UUID4)")
    )
    column = models.ForeignKey(
        BoardColumn, on_delete=models.CASCADE, related_name="items"
    )
    object_type = models.CharField(
        _("object type"),
        max_length=50,
        choices=BoardObjectTypes.choices,
        default=BoardObjectTypes.zaak,
        help_text=_("Type of the board item"),
    )
    object = models.URLField(
        _("object"),
        db_index=True,
        help_text=_(
            "URL-reference of the OBJECT in one of ZGW APIs this board item relates to"
        ),
    )

    objects = BoardItemQuerySet.as_manager()

    class Meta:
        verbose_name = _("board item")
        verbose_name_plural = _("board items")

    def zaak_document(self):
        if self.object_type != BoardObjectTypes.zaak:
            return None

        return get_zaak_document(self.object)
