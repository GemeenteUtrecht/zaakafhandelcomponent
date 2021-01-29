from urllib.parse import urlencode, urljoin

from django.core.validators import URLValidator
from django.urls import reverse

from rest_framework import serializers

from zac.accounts.serializers import UserSerializer
from zac.core.utils import get_ui_url


class ErrorSerializer(serializers.Serializer):
    error = serializers.CharField()


class RecursiveField(serializers.Serializer):
    def to_representation(self, instance):
        return self.parent.parent.to_representation(instance)


class TaskSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    execute_url = serializers.SerializerMethodField(validators=[URLValidator])
    name = serializers.CharField(max_length=100)
    created = serializers.DateTimeField()
    has_form = serializers.BooleanField()
    assignee = UserSerializer(allow_null=True, required=False)

    def get_execute_url(self, obj) -> str:
        core_zaak_task_url = reverse("core:zaak-task", args=[obj.id])
        params = {
            "returnUrl": get_ui_url(
                [
                    "ui",
                    "zaken",
                    self.context["zaak"].bronorganisatie,
                    self.context["zaak"].identificatie,
                ]
            )
        }

        return get_ui_url([core_zaak_task_url], params=params)


class ProcessInstanceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    definition_id = serializers.CharField(max_length=1000)
    title = serializers.CharField(max_length=100)
    sub_processes = RecursiveField(many=True)
    messages = serializers.ListField(
        child=serializers.CharField(max_length=100), allow_empty=True
    )
    tasks = TaskSerializer(many=True)
