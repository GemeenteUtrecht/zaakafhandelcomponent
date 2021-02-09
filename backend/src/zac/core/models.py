from django.db import models
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes


class CoreConfig(SingletonModel):
    primary_drc = models.ForeignKey(
        "zgw_consumers.Service",
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"api_type": APITypes.drc},
        related_name="+",
    )
    primary_brc = models.ForeignKey(
        "zgw_consumers.Service",
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"api_type": APITypes.brc},
        related_name="+",
    )

    app_id = models.URLField(
        _("BPTL Application ID"),
        help_text=_(
            "A (globally) unique ID of the BPTL application. In this case the URL that points to the appropriate"
            "application on the Openzaak Autorisaties API."
        ),
        default="",
    )

    class Meta:
        verbose_name = _("global configuration")

    def __str__(self):
        return force_str(self._meta.verbose_name)
