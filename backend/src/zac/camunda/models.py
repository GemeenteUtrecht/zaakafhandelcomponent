from django.db import models
from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel
from zgw_consumers.constants import APITypes


class BPTLAppId(SingletonModel):
    app_id = models.URLField(
        _("BPTL Application ID"),
        help_text=_(
            "A (globally) unique ID of the BPTL application. In this case the URL that points to the appropriate"
            "application on the Openzaak Autorisaties API."
        ),
    )

    label = models.CharField(
        _("label"),
        max_length=100,
        help_text=_("Human readable application identifier."),
    )

    class Meta:
        verbose_name = _("BPTL Application ID")

    def __str__(self):
        return force_text(self._meta.verbose_name)
