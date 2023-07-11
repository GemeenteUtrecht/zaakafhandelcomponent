from django.contrib.auth.models import Group
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from zac.accounts.api.fields import UserSlugRelatedField
from zac.accounts.api.serializers import GroupSerializer, UserSerializer
from zac.accounts.models import User
from zac.utils.validators import ImmutableFieldValidator

from ..models import Activity, Event
from .permission_loaders import add_permissions_for_activity_assignee


class EventSerializer(serializers.ModelSerializer):
    created_by = UserSlugRelatedField(
        slug_field="username",
        queryset=User.objects.prefetch_related("groups").all(),
        required=False,
        help_text=_("`username` of the user assigned to answer."),
        allow_null=True,
    )

    class Meta:
        model = Event
        fields = (
            "id",
            "activity",
            "notes",
            "created",
            "created_by",
        )


class ReadActivitySerializer(serializers.ModelSerializer):
    created_by = UserSerializer()
    group_assignee = GroupSerializer(
        required=False,
        help_text=_("Group assigned to activity."),
    )
    user_assignee = UserSerializer(
        required=False,
        help_text=_("User assigned to activity."),
    )
    events = EventSerializer(many=True, read_only=True)

    class Meta:
        model = Activity
        fields = (
            "created",
            "created_by",
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
                "view_name": "activity-detail",
            },
        }


class CreateOrUpdateActivitySerializer(serializers.ModelSerializer):
    group_assignee = serializers.SlugRelatedField(
        slug_field="name",
        queryset=Group.objects.prefetch_related("user_set").all(),
        required=False,
        help_text=_("Name of the group."),
    )
    user_assignee = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        required=False,
        help_text=_("`username` of the user."),
    )
    events = EventSerializer(many=True, read_only=True)

    class Meta:
        model = Activity
        fields = (
            "created",
            "created_by",
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
                "view_name": "activity-detail",
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
        self._add_permissions_for_activity_assignee(activity)
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
