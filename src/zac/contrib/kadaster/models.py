from django.db import models
from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel


class KadasterConfig(SingletonModel):
    locatieserver = models.URLField(
        _("root URL locatieserver"),
        default="https://geodata.nationaalgeoregister.nl/locatieserver/v3/",
    )
    bag_api = models.URLField(
        _("root URL BAG API"),
        default="https://bag.basisregistraties.overheid.nl/api/v1/",
    )
    api_key = models.CharField(
        _("API key"), max_length=255, blank=True, help_text=_("API key used for BAG."),
    )

    class Meta:
        verbose_name = _("kadasterconfiguratie")

    def __str__(self):
        return force_text(self._meta.verbose_name)

    def save(self, *args, **kwargs):
        if not self.locatieserver.endswith("/"):
            self.locatieserver = f"{self.locatieserver}/"

        if not self.bag_api.endswith("/"):
            self.bag_api = f"{self.bag_api}/"

        super().save(*args, **kwargs)
