from datetime import date

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers


class AccessLogUserReportSerializer(serializers.Serializer):
    naam = serializers.CharField()
    email = serializers.EmailField()
    gebruikersnaam = serializers.CharField()
    total_logins = serializers.IntegerField()
    logins_per_day = serializers.DictField(child=serializers.IntegerField())


class BaseCountSerializer(serializers.Serializer):
    """Base serializer to return counts for different actions."""

    count = serializers.IntegerField(allow_null=True, help_text="")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Subclasses should override help_text
        if hasattr(self, "help_text"):
            self.fields["count"].help_text = self.help_text


class AxesResetSerializer(BaseCountSerializer):
    """Serializer for resetting access attempts."""

    help_text = _("Number of cleared access attempts.")


class AddBlueprintPermissionsSerializer(BaseCountSerializer):
    """Serializer for adding blueprint permissions."""

    help_text = _("Number of blueprint permissions added.")


class UserLogSerializer(serializers.Serializer):
    recipient_list = serializers.ListField(
        child=serializers.EmailField(help_text=_("Email of recipient."), required=True),
        required=True,
    )
    start_date = serializers.DateField(
        default=date.today,
        help_text=_("Start date of logs."),
        required=False,
    )
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        data = super().validate(attrs)
        # If start_date wasn't provided, use today's date
        start_date = data.get("start_date") or date.today()
        end_date = data.get("end_date")

        if end_date and end_date <= start_date:
            raise serializers.ValidationError(
                _("Start date needs to be earlier than end date.")
            )
        return data
