from django.db import models
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes


class DowcConfigManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("service")


class DowcConfig(SingletonModel):
    """
    A singleton model to configure the required credentials to communicate with the "DoWC".
    """

    service = models.ForeignKey(
        "zgw_consumers.Service",
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"api_type": APITypes.orc},
    )

    objects = DowcConfigManager()

    class Meta:
        verbose_name = _("Dowc configuration")

    def __str__(self):
        return force_str(self._meta.verbose_name)
