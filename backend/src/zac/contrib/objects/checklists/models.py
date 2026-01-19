from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ChecklistLock(models.Model):
    """
    A model that keeps track of checklist locks.

    Because checklists are stored in the OBJECTS API the consumer API (in this case the ZAC)
    of the OBJECTS API is deemed responsible for object manipulation management.

    """

    url = models.URLField(unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    zaak = models.URLField(unique=True)
    zaak_identificatie = models.CharField(max_length=255, blank=True)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = _("Checklist lock")
        verbose_name_plural = _("Checklist locks")

    def __str__(self):
        return f"Checklist for ZAAK: `{self.zaak_identificatie}` is locked by: `{self.user}`."
