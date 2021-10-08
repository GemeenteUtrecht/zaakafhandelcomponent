from django.contrib.auth.models import Group
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
    group_assignee = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Group.objects.prefetch_related("user_set").all(),
        required=False,
    )
    user_assignee = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        required=False,
    )
    events = EventSerializer(many=True, read_only=True)

    class Meta:
        model = Activity
        fields = (
            "document",
            "events",
            "group_assignee",
            "id",
            "name",
            "remarks",
            "status",
            "user_assignee",
            "zaak",
            "url",
        )
        extra_kwargs = {
            "url": {
                "view_name": "activities:activity-detail",
            },
            "zaak": {"validators": (ImmutableFieldValidator(),)},
        }

    def validate(self, attrs):
        if attrs.get("user_assignee") and attrs.get("group_assignee"):
            raise serializers.ValidationError(
                "An activity can not be assigned to both a user and a group."
            )
        return attrs

    def _add_permissions_for_activity_assignee(self, activity):
        if activity.user_assignee:
            add_permissions_for_activity_assignee(activity, activity.user_assignee)
        if activity.group_assignee:
            users = activity.group_assignee.user_set.all()
            for user in users:
                add_permissions_for_activity_assignee(activity, user)

    @transaction.atomic
    def create(self, validated_data):
        activity = super().create(validated_data)
        # add permissions to assignee
        self._add_permissions_for_activity_assignee()
        return activity

    @transaction.atomic
    def update(self, instance, validated_data):
        user_assignee = validated_data.get("user_assignee")
        group_assignee = validated_data.get("group_assignee")
        grant_permissions = (
            user_assignee
            or group_assignee
            and (
                user_assignee != instance.user_assignee
                or group_assignee != instance.group_assignee
            )
        )
        if user_assignee:
            validated_data["group_assignee"] = None
        if group_assignee:
            validated_data["user_assignee"] = None

        activity = super().update(instance, validated_data)

        # add permissions to assignee
        if grant_permissions:
            self._add_permissions_for_activity_assignee(activity)
        return activity
