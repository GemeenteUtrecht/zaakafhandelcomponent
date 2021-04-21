from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from zac.accounts.models import User
from zac.utils.validators import ImmutableFieldValidator

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


class ActivitySerializer(serializers.ModelSerializer):
    assignee = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        required=False,
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
            "zaak": {"validators": (ImmutableFieldValidator(),)},
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
        grant_permissions = (
            validated_data.get("assignee")
            and validated_data.get("assignee") != instance.assignee
        )
        activity = super().update(instance, validated_data)

        # add permissions to assignee
        if grant_permissions:
            add_permissions_for_activity_assignee(activity)
        return activity
