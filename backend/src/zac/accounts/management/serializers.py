from datetime import date

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers


class AccessLogUserReportSerializer(serializers.Serializer):
    naam = serializers.CharField()
    email = serializers.EmailField()
    gebruikersnaam = serializers.CharField()
    totalLogins = serializers.IntegerField(source="total_logins")
    loginsPerDay = serializers.DictField(
        source="logins_per_day",
        child=serializers.IntegerField(min_value=0),
    )


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
    start_period = serializers.DateTimeField(
        required=True,
        help_text=_("Start date of the period for which the report is generated."),
    )
    end_period = serializers.DateTimeField(
        required=True,
        help_text=_("End date of the period for which the report is generated."),
    )

    def validate(self, attrs):
        data = super().validate(attrs)
        # If start_period wasn't provided, use today's date
        start_period = data.get("start_period") or date.today()
        end_period = data.get("end_period")

        if end_period and end_period <= start_period:
            raise serializers.ValidationError(
                _("Start date needs to be earlier than end date.")
            )
        return data
