from django.db import transaction

from rest_framework import serializers

from zac.accounts.models import User

from ..models import Activity, Event
from .permission_loaders import add_permissions_for_activity_assignee


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = (
            "id",
            "activity",
            "notes",
            "created",
        )


class ActivitySerializer(serializers.HyperlinkedModelSerializer):
    assignee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    events = EventSerializer(many=True, read_only=True)

    class Meta:
        model = Activity
        fields = (
            "id",
            "url",
            "zaak",
            "name",
            "remarks",
            "status",
            "assignee",
            "document",
            "created",
            "events",
        )
        extra_kwargs = {
            "url": {
                "view_name": "activities:activity-detail",
            },
        }

    @transaction.atomic
    def create(self, validated_data):
        activity = super().create(validated_data)

        # add permissions to assignee
        if activity.assignee:
            add_permissions_for_activity_assignee(activity)
        return activity

    @transaction.atomic
    def update(self, instance, validated_data):
        activity = super().update(instance, validated_data)

        # add permissions to assignee
        if (
            validated_data.get("assignee")
            and validated_data.get("assignee") != instance.assignee
        ):
            add_permissions_for_activity_assignee(activity)
        return activity
