from django.utils.translation import ugettext_lazy as _

from rest_framework import fields

from zac.utils.filters import ApiFilterSet


class ProcessInstanceFilterSet(ApiFilterSet):
    zaakUrl = fields.URLField(
        required=True, help_text=_("URL-reference of related ZAAK.")
    )
    includeBijdragezaak = fields.BooleanField(
        required=False,
        help_text=_(
            "A boolean flag that allows an end user to explicitely retrieve (sub) process instances related to the ZAAK."
        ),
        default=False,
    )
