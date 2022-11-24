from django.utils.translation import ugettext_lazy as _

from rest_framework import fields

from zac.utils.filters import ApiFilterSet


class ProcessInstanceFilterSet(ApiFilterSet):
    zaak_url = fields.URLField(
        required=True, help_text=_("URL-reference of related ZAAK.")
    )
    include_subprocess = fields.BooleanField(
        required=False,
        help_text=_(
            "A boolean flag that allows an end user to explicitely specify only super level process instances."
        ),
        default=False,
    )
