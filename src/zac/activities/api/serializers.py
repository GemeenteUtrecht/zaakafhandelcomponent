from rest_framework import serializers

from ..models import Activity, Event


class ActivitySerializer(serializers.ModelSerializer):
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
        )
