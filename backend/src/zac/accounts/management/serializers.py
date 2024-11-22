from datetime import date

from django.utils.translation import gettext_lazy as _

from rest_framework.serializers import (
    DateField,
    EmailField,
    IntegerField,
    ListField,
    Serializer,
    ValidationError,
)


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
    start_date = DateField(
        default=date.today(), help_text=_("Start date of logs."), required=False
    )
    end_date = DateField(required=False)

    def validate(self, attrs):
        data = super().validate(attrs)
        if (end_date := data.get("end_date")) and (end_date <= data["start_date"]):
            raise ValidationError(_("Start date needs to be earlier than end date."))
        return data
