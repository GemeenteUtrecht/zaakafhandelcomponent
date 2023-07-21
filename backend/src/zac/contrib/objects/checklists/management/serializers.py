from django.utils.translation import gettext_lazy as _

from rest_framework.serializers import IntegerField, Serializer


class UnlockCountSerializer(Serializer):
    count = IntegerField(
        help_text=_("Number of checklists that are unlocked."), allow_null=True
    )
