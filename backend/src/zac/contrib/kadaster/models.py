from django.db import models
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes


class KadasterConfig(SingletonModel):
    """
    A singleton model to configure the required credentials to communicate with the "Kadaster".
    """

    locatieserver = models.URLField(
        _("root URL locatieserver"),
        default="https://geodata.nationaalgeoregister.nl/locatieserver/v3/",
    )
    service = models.ForeignKey(
        "zgw_consumers.Service",
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"api_type": APITypes.orc},
        verbose_name=_("service"),
        help_text=_(
            "Configuration for the service that makes requests to the BAG API."
        ),
    )

    class Meta:
        verbose_name = _("kadasterconfiguratie")

    def __str__(self):
        return force_str(self._meta.verbose_name)

    def save(self, *args, **kwargs):
        if not self.locatieserver.endswith("/"):
            self.locatieserver = f"{self.locatieserver}/"

        super().save(*args, **kwargs)
