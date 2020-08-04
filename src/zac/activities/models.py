from django.conf import settings
from django.db import models
from django.template.defaultfilters import truncatewords
from django.utils.translation import gettext_lazy as _

from .constants import ActivityStatuses


class Activity(models.Model):
    """
    Represent a single ad-hoc activity.
    """

    zaak = models.URLField(
        _("zaak URL"),
        max_length=1000,
        help_text=_("URL reference to the zaak in its API"),
    )
    name = models.CharField(_("name"), max_length=100)
    remarks = models.TextField(_("remarks"), blank=True)
    status = models.CharField(
        _("status"),
        max_length=50,
        choices=ActivityStatuses.choices,
        default=ActivityStatuses.on_going,
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        verbose_name=_("assignee"),
        help_text=_("Person responsible for managing this activity."),
        on_delete=models.SET_NULL,
    )
    document = models.URLField(
        _("document URL"),
        max_length=1000,
        blank=True,
        help_text=_("Document in the Documents API."),
    )

    created = models.DateTimeField(_("created"), auto_now_add=True)

    class Meta:
        verbose_name = _("activity")
        verbose_name_plural = _("activities")
        unique_together = (("zaak", "name"),)

    def __str__(self):
        return self.name


class Event(models.Model):
    """
    Represent a single log-entry worthy event for a given activity.
    """

    activity = models.ForeignKey("Activity", on_delete=models.CASCADE)
    notes = models.TextField(_("notes"))
    created = models.DateTimeField(_("created"), auto_now_add=True)

    class Meta:
        verbose_name = _("activity event")
        verbose_name_plural = _("activity events")

    def __str__(self):
        return truncatewords(self.notes, 8)
