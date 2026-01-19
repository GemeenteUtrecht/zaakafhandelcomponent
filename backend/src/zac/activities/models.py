from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models
from django.template.defaultfilters import truncatewords
from django.utils.translation import gettext_lazy as _

from ..accounts.models import User
from .constants import ActivityStatuses
from .query import ActivityQuerySet


class Activity(models.Model):
    """
    An activity can be any question or task not currently handled by a pre-defined, programmed business task.
    """

    zaak = models.URLField(
        _("ZAAK-URL"),
        max_length=1000,
        help_text=_("URL-reference to the ZAAK in its API"),
    )
    name = models.CharField(_("name"), max_length=100)
    remarks = models.TextField(_("remarks"), blank=True)
    created_by = models.ForeignKey(
        User,
        related_name="activities_created",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    status = models.CharField(
        _("status"),
        max_length=50,
        choices=ActivityStatuses.choices,
        default=ActivityStatuses.on_going,
    )
    user_assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        verbose_name=_("user assignee"),
        help_text=_("Person responsible for managing this activity."),
        on_delete=models.SET_NULL,
    )
    group_assignee = models.ForeignKey(
        Group,
        null=True,
        blank=True,
        verbose_name=_("group assignee"),
        help_text=_("Group responsible for managing this activity."),
        on_delete=models.SET_NULL,
    )

    document = models.URLField(
        _("document URL"),
        max_length=1000,
        blank=True,
        help_text=_("Document in the Documents API."),
    )

    created = models.DateTimeField(_("created"), auto_now_add=True)

    objects = ActivityQuerySet.as_manager()

    class Meta:
        verbose_name = _("activity")
        verbose_name_plural = _("activities")
        constraints = [
            models.UniqueConstraint(
                fields=["zaak", "name"],
                name="unique_zaak_name",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.user_assignee and self.group_assignee:
            raise ValidationError(
                "An activity can not be assigned to both a user and a group."
            )
        return super().save(*args, **kwargs)


class Event(models.Model):
    """
    An event is related to the an activity and comprises a log-entry worthy event for a given activity.
    """

    activity = models.ForeignKey(
        "Activity",
        on_delete=models.CASCADE,
        related_name="events",
    )
    notes = models.TextField(_("notes"))
    created = models.DateTimeField(_("created"), auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        related_name="events_created",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = _("activity event")
        verbose_name_plural = _("activity events")

    def __str__(self):
        return truncatewords(self.notes, 8)
