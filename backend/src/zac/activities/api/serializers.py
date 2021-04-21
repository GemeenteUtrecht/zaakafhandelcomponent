from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from zac.accounts.models import User
from zac.utils.validators import ImmutableFieldValidator

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
    assignee = serializers.SlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        allow_blank=True,
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
