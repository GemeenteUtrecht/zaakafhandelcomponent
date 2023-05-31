from django.utils.translation import gettext_lazy as _

from rest_framework.serializers import IntegerField, Serializer


class AxesResetSerializer(Serializer):
    count = IntegerField(
        help_text=_("Number of cleared access attempts."), allow_null=True
    )
