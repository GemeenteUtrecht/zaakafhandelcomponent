from typing import List, NoReturn

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from zac.accounts.serializers import UserSerializer
from zac.api.polymorphism import PolymorphicSerializer

from ..user_tasks.context import REGISTRY


class ErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()


class RecursiveField(serializers.Serializer):
    def to_representation(self, instance):
        return self.parent.parent.to_representation(instance)


class TaskSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    execute_url = serializers.URLField()
    name = serializers.CharField(max_length=100)
    created = serializers.DateTimeField()
    has_form = serializers.BooleanField()
    assignee = UserSerializer(allow_null=True, required=False)


class ProcessInstanceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    definition_id = serializers.CharField(max_length=1000)
    title = serializers.CharField(max_length=100)
    sub_processes = RecursiveField(many=True)
    messages = serializers.ListField(
        child=serializers.CharField(max_length=100), allow_empty=True
    )
    tasks = TaskSerializer(many=True)


class UserTaskContextSerializer(PolymorphicSerializer):
    discriminator_field = "form"
    serializer_mapping = {}  # set at run-time based on the REGISTRY

    form = serializers.ChoiceField(
        label=_("Form to render"),
        source="task.form_key",
        help_text=_(
            "The form key of the form to render. Note that unknown form keys (= not "
            "present in the enum) will be returned as is."
        ),
        allow_blank=True,
        choices=(),
    )
    task = TaskSerializer(label=_("User task summary"))
    # the context is added by the serializer_mapping serializers

    def __init__(self, *args, **kwargs):

        self.serializer_mapping = {
            form_key: serializer
            for form_key, (callback, serializer) in REGISTRY.items()
        }

        super().__init__(*args, **kwargs)

        self.fields["form"].choices = list(REGISTRY.keys())


class MessageSerializer(serializers.Serializer):
    process_instance_id = serializers.UUIDField(
        label=_("Process instance ID"),
        help_text=_("The ID of the process instance where the message is sent to."),
    )
    message = serializers.ChoiceField(
        choices=(),
        label=_("Message"),
        help_text=_("The message that is sent to the process instance."),
    )

    def set_message_choices(self, message_names: List[str]) -> NoReturn:
        self.fields["message"].choices = [(name, name) for name in message_names]
