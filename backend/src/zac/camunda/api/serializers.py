from typing import Any, Dict, List

from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.fields import _UnvalidatedField

from zac.accounts.api.serializers import GroupSerializer, UserSerializer
from zac.accounts.models import User
from zac.api.polymorphism import PolymorphicSerializer

from ..constants import AssigneeTypeChoices
from ..user_tasks.context import REGISTRY
from .fields import TaskField
from .validators import GroupValidator, OrValidator, UserValidator


class ErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()


class RecursiveField(serializers.Serializer):
    def to_representation(self, instance):
        return self.parent.parent.to_representation(instance)


class TaskAssigneeUserSerializer(serializers.Serializer):
    assignee = UserSerializer()


class TaskAssigneeGroupSerializer(serializers.Serializer):
    assignee = GroupSerializer()


class TaskAssigneeFallbackSerializer(serializers.Serializer):
    assignee = serializers.CharField(default="", allow_blank=True)


class TaskSerializer(PolymorphicSerializer):
    serializer_mapping = {
        AssigneeTypeChoices.user: TaskAssigneeUserSerializer,
        AssigneeTypeChoices.group: TaskAssigneeGroupSerializer,
        "": TaskAssigneeFallbackSerializer,
    }
    discriminator_field = "assignee_type"
    fallback_distriminator_value = ""

    id = serializers.UUIDField()
    name = serializers.CharField(max_length=100)
    created = serializers.DateTimeField()
    has_form = serializers.BooleanField()
    assignee_type = serializers.ChoiceField(
        required=True,
        choices=AssigneeTypeChoices.choices + ("", ""),
        help_text=_("The assignee type that was assigned to the user task."),
    )


class ProcessInstanceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    definition_id = serializers.CharField(max_length=1000)
    title = serializers.CharField(max_length=100)
    sub_processes = RecursiveField(many=True)
    messages = serializers.ListField(
        child=serializers.CharField(max_length=100), allow_empty=True
    )
    tasks = TaskSerializer(many=True)


class ChoiceFieldNoValidation(_UnvalidatedField, serializers.ChoiceField):
    pass


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
        help_text=_("The ID of the task to which the assignee/delegate is to be set."),
    )
    assignee = serializers.CharField(
        label=_("assignee"),
        help_text=_("Assignee of the task."),
        allow_blank=True,
        validators=(OrValidator(UserValidator(), GroupValidator()),),
    )
    delegate = serializers.CharField(
        label=_("delegate"),
        help_text=_("Delegate of the task."),
        allow_blank=True,
        validators=(OrValidator(UserValidator(), GroupValidator()),),
    )

    def _resolve_name(self, name: str) -> str:
        try:
            User.objects.get(username=name)
            return f"user:{name}"
        except User.DoesNotExist:
            pass

        try:
            Group.objects.get(name=name)
            return f"group:{name}"
        except Group.DoesNotExist:
            pass

        return name

    def validate_assignee(self, assignee: str) -> str:
        return self._resolve_name(assignee)

    def validate_delegate(self, delegate: str) -> str:
        return self._resolve_name(delegate)
