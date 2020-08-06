from rest_framework import serializers

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


class ActivitySerializer(serializers.ModelSerializer):
    events = EventSerializer(many=True, read_only=True)

    class Meta:
        model = Activity
        fields = (
            "id",
            "zaak",
            "name",
            "remarks",
            "status",
            "assignee",
            "document",
            "created",
            "events",
        )
