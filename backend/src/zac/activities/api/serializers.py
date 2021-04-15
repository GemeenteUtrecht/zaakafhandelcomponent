from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from backend.src.zac.camunda.api.validators import UserValidator
from zac.accounts.api.serializers import UserSerializer
from zac.camunda.api.validators import UserValidator
from zac.core.camunda.select_documents import DocumentSerializer

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
    assignee = UserSerializer()
    events = EventSerializer(many=True, read_only=True)
    document = DocumentSerializer(read_only=True)

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


class PatchActivitySerializer(ActivitySerializer):
    assignee = serializers.CharField(
        label=_("assignee"),
        help_text=_("User assigned to the activity."),
        allow_blank=True,
        validators=(UserValidator(),),
    )
    document = serializers.URLField(
        label=_("activity document url"),
        help_text=_("URL that points to the document."),
        allow_blank=True,
    )

    class Meta(ActivitySerializer.Meta):
        fields = (
            "assignee",
            "document",
            "status",
        )
