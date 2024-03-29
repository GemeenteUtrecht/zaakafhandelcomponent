from django.db import models
from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes


class BRPConfigManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("service")


class BRPConfig(SingletonModel):
    """
    A singleton model to configure the required credentials to communicate with the "BRP".
    """

    service = models.ForeignKey(
        "zgw_consumers.Service",
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"api_type": APITypes.orc},
    )

    objects = BRPConfigManager()

    class Meta:
        verbose_name = _("BRP configuration")

    def __str__(self):
        return force_text(self._meta.verbose_name)
