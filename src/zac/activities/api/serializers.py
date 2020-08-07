from rest_framework import serializers

from zac.accounts.models import User

from ..models import Activity, Event


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
        queryset=User.objects.filter(is_active=True), required=False, allow_null=True,
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
            "url": {"view_name": "activities:activity-detail",},
        }
