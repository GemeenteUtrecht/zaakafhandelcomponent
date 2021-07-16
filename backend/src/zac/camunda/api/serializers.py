from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from zac.accounts.api.serializers import UserSerializer
from zac.api.polymorphism import PolymorphicSerializer

from ..user_tasks.context import REGISTRY
from .fields import TaskField
from .validators import UserValidator


class ErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()


class RecursiveField(serializers.Serializer):
    def to_representation(self, instance):
        return self.parent.parent.to_representation(instance)


class TaskSerializer(serializers.Serializer):
    id = serializers.UUIDField()
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


class ChoiceFieldNoValidation(serializers.ChoiceField):
    def to_internal_value(self, data):
        return data


class BaseUserTaskSerializer(PolymorphicSerializer):
    discriminator_field = "form"
    serializer_mapping = {}  # set at run-time based on the REGISTRY
    fallback_distriminator_value = ""  # fall back to dynamic form

    form = ChoiceFieldNoValidation(
        label=_("Form to render"),
        source="task.form_key",
        help_text=_(
            "The form key of the form to render. Note that unknown form keys (= not "
            "present in the enum) will be returned as is."
        ),
        allow_blank=True,
        choices=(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["form"].choices = [
            (key, key or _("(camunda form)")) for key in REGISTRY.keys()
        ]


class UserTaskContextSerializer(BaseUserTaskSerializer):
    task = TaskSerializer(label=_("User task summary"))
    # the context is added by the serializer_mapping serializers

    def __init__(self, *args, **kwargs):
        self.serializer_mapping = {
            form_key: item.read_serializer for form_key, item in REGISTRY.items()
        }
        super().__init__(*args, **kwargs)


class SubmitUserTaskSerializer(BaseUserTaskSerializer):
    def __init__(self, *args, **kwargs):
        self.serializer_mapping = {
            form_key: item.write_serializer
            for form_key, item in REGISTRY.items()
            if item.write_serializer
        }
        super().__init__(*args, **kwargs)

    def get_mapped_serializer(self):
        form_key = self.context["task"].form_key
        lookup = (
            form_key
            if form_key in self.serializer_mapping
            else self.fallback_distriminator_value
        )
        return self.serializer_mapping[lookup]

    def on_task_submission(self) -> Any:
        mapped_serializer = self.get_mapped_serializer()
        if hasattr(mapped_serializer, "on_task_submission"):
            return mapped_serializer.on_task_submission()

    def get_process_variables(self) -> Dict:
        mapped_serializer = self.get_mapped_serializer()
        if hasattr(
            mapped_serializer,
            "get_process_variables",
        ):
            return mapped_serializer.get_process_variables()
        return {}


class MessageSerializer(serializers.Serializer):
    process_instance_id = serializers.UUIDField(
        label=_("Process instance ID"),
        help_text=_("The ID of the process instance where the message is sent to."),
    )
    message = serializers.ChoiceField(
        choices=(("", ""),),
        label=_("Message"),
        help_text=_("The message that is sent to the process instance."),
    )

    def set_message_choices(self, message_names: List[str]):
        self.fields["message"].choices = [(name, name) for name in message_names]


class SetTaskAssigneeSerializer(serializers.Serializer):
    task = TaskField(
        label=_("Task ID"),
        help_text=_("The ID of the task which assignee/delegate is to be set."),
    )
    assignee = serializers.CharField(
        label=_("assignee"),
        help_text=_("User assigned to the task."),
        allow_blank=True,
        validators=(UserValidator(),),
    )
    delegate = serializers.CharField(
        label=_("delegate"),
        help_text=_("User delegated to the task."),
        allow_blank=True,
        validators=(UserValidator(),),
    )
