from django.utils.translation import gettext_lazy as _

from rest_framework.serializers import EmailField, IntegerField, ListField, Serializer


class AxesResetSerializer(Serializer):
    count = IntegerField(
        help_text=_("Number of cleared access attempts."), allow_null=True
    )


class AddBlueprintPermissionsSerializer(Serializer):
    count = IntegerField(
        help_text=_("Number of blueprint permissions added."), allow_null=True
    )


class UserLogSerializer(Serializer):
    recipient_list = ListField(
        child=EmailField(help_text=_("Email of recipient."), required=True),
        required=True,
    )
