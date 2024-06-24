from django.utils.translation import ugettext_lazy as _

from rest_framework import fields

from zac.utils.filters import ApiFilterSet


class reviewFilterSet(ApiFilterSet):
    assignee = fields.CharField(required=True, help_text=_("Assignee of the review."))
