from django.db import models
from django.utils.translation import ugettext_lazy as _

from .constants import APITypes


class Service(models.Model):
    label = models.CharField(_("label"), max_length=100)
    api_type = models.CharField(_("type"), max_length=20, choices=APITypes.choices)
    api_root = models.CharField(_("api root url"), max_length=255, unique=True)

    # credentials for the API
    client_id = models.CharField(max_length=255, blank=True)
    secret = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = _("service")
        verbose_name_plural = _("services")

    def __str__(self):
        return f"[{self.get_api_type_display()}] {self.label}"

    def save(self, *args, **kwargs):
        if not self.api_root.endswith('/'):
            self.api_root = f"{self.api_root}/"
        super().save(*args, **kwargs)
