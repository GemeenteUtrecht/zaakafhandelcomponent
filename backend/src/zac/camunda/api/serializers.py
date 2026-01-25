from typing import Any, Dict, List

from django.conf import settings
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from requests.exceptions import HTTPError
from rest_framework import serializers
from rest_framework_dataclasses.serializers import DataclassSerializer
from zds_client.client import ClientError
from zgw_consumers.concurrent import parallel

from zac.accounts.api.serializers import GroupSerializer, UserSerializer
from zac.accounts.models import User
from zac.api.polymorphism import PolymorphicSerializer
from zac.camunda.api.data import HistoricUserTask
from zac.camunda.api.fields import TaskField
from zac.camunda.api.validators import GroupValidator, OrValidator, UserValidator
from zac.camunda.constants import AssigneeTypeChoices
from zac.camunda.data import BPMN, Task
from zac.camunda.process_instances import (
    get_process_instance,
    get_top_level_process_instances,
    update_process_instance_variable,
)
from zac.camunda.user_tasks.api import get_killability_of_task, get_task, set_assignee
from zac.camunda.user_tasks.context import REGISTRY
from zac.core.camunda.utils import resolve_assignee
from zac.core.rollen import Rol
from zac.core.services import fetch_rol, get_zaak
from zgw.models.zrc import Zaak


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
        help_text=_("The `assigneeType` of the user task."),
    )
    can_cancel_task = serializers.SerializerMethodField()
    form_key = serializers.CharField(max_length=255, allow_null=True, allow_blank=True)

    def get_can_cancel_task(self, obj) -> bool:
        return obj.name in self.context.get("killable_tasks", [])


class ProcessInstanceSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text=_("Process instance `id`."))
    definition_id = serializers.CharField(max_length=1000)
    title = serializers.CharField(max_length=100)
    sub_processes = RecursiveField(many=True)
    messages = serializers.ListField(
        child=serializers.CharField(max_length=100), allow_empty=True
    )
    tasks = TaskSerializer(many=True)


class CreateZaakRedirectCheckSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text=_("Process instance `id`."))
    zaak = serializers.URLField(help_text=_("Reference to ZAAK."), required=False)

    def validate(self, attrs):
        process_instance = get_process_instance(attrs["id"])
        try:
            process_instance.get_variable("zaakDetailUrl")
            zaak_url = process_instance.get_variable("zaakUrl")
            attrs["zaak"] = zaak_url
        except HTTPError as exc:
            if exc.response.status_code == 404:
                raise serializers.ValidationError(exc.response.json()["message"])
            else:
                raise exc
        return attrs


class ProcessInstanceMessageSerializer(serializers.Serializer):
    id = serializers.UUIDField(
        help_text=_("Process instance `id`. Used to correlate message to.")
    )
    messages = serializers.ListField(
        child=serializers.CharField(max_length=100), allow_empty=True
    )


class ChoiceFieldNoValidation(serializers.ChoiceField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allow_blank = True
        self.allow_null = True

    def to_internal_value(self, data):
        return data

    def to_representation(self, value):
        return value


class BaseUserTaskSerializer(PolymorphicSerializer):
    discriminator_field = "form"
    serializer_mapping = {}  # set at run-time based on the REGISTRY
    fallback_distriminator_value = ""  # fall back to dynamic form

    form = ChoiceFieldNoValidation(
        label=_("Form to render"),
        source="task.form_key",
        help_text=_(
            "The `formKey` of the form to render. Note that unknown `formKeys` (= not "
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
        return dict()


class MessageSerializer(serializers.Serializer):
    process_instance_id = serializers.UUIDField(
        label=_("Process instance `id`"),
        help_text=_("The `id` of the process instance where the message is sent to."),
    )
    message = serializers.ChoiceField(
        choices=(("", ""),),
        label=_("Message"),
        help_text=_("The message that is sent to the process instance."),
    )

    def set_message_choices(self, message_names: List[str]):
        self.fields["message"].choices = [(name, name) for name in message_names]


class MessageVariablesSerializer(serializers.Serializer):
    waitForIt = serializers.BooleanField(
        label=_("Wait for it"),
        help_text=_("Wait for a change in fetch-process-instances if this is True."),
        default=False,
    )


class SetTaskAssigneeSerializer(serializers.Serializer):
    task = TaskField(
        label=_("Task `id`"),
        help_text=_(
            "The `id` of the task to which the assignee/delegate is to be set."
        ),
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
        user_or_group = resolve_assignee(name)
        if isinstance(user_or_group, User):
            return f"{AssigneeTypeChoices.user}:{user_or_group}"
        return f"{AssigneeTypeChoices.group}:{user_or_group}"

    def validate_assignee(self, assignee: str) -> str:
        if assignee:
            return self._resolve_name(assignee)
        return assignee

    def validate_delegate(self, delegate: str) -> str:
        if delegate:
            return self._resolve_name(delegate)
        return delegate


class BPMNSerializer(DataclassSerializer):
    class Meta:
        dataclass = BPMN
        fields = (
            "id",
            "bpmn20_xml",
        )
        extra_kwargs = {
            "id": {
                "help_text": _("The process definition `id`."),
            },
            "bpmn20_xml": {
                "help_text": _(
                    "The XML of the process definition. To be used for visualization of the BPMN."
                )
            },
        }


class HistoricActivityInstanceDetailSerializer(serializers.Serializer):
    naam = serializers.CharField(
        source="variable_name", help_text=_("Name of user task variable.")
    )
    waarde = serializers.SerializerMethodField(
        help_text=_("Value of user task variable.")
    )
    label = serializers.CharField(
        required=False,
        help_text=_("Label of user task variable in the Camunda user task form."),
    )

    def get_waarde(self, obj) -> Any:
        return obj.get("value")


class HistoricUserTaskSerializer(DataclassSerializer):
    assignee = serializers.SerializerMethodField(
        help_text=_("Full name of user or group assigned to user task."),
    )
    completed = serializers.DateTimeField(
        source="task.end_time", help_text=_("Datetime user task was completed.")
    )
    created = serializers.DateTimeField(
        source="task.created", help_text=_("Datetime user task was created.")
    )
    name = serializers.CharField(source="task.name", help_text=_("Name of user task."))
    history = HistoricActivityInstanceDetailSerializer(
        many=True, help_text=_("List of variables set by the user task.")
    )

    class Meta:
        dataclass = HistoricUserTask
        fields = (
            "assignee",
            "completed",
            "created",
            "name",
            "history",
        )

    def get_assignee(self, obj) -> str:
        if isinstance(obj.assignee, User):
            return obj.assignee.get_full_name()
        elif isinstance(obj.assignee, Group):
            return f"Groep: {obj.assignee.name.lower()}"
        return ""


class CancelTaskSerializer(serializers.Serializer):
    task = serializers.UUIDField(
        help_text=_("The UUID of the task that is to be canceled.")
    )

    def validate_task(self, task_id: str) -> Task:
        task = get_task(task_id)
        if not task:
            raise serializers.ValidationError(
                _("No task found for id `{task_id}`".format(task_id=task_id))
            )
        killable = get_killability_of_task(task.name)
        if not killable:
            raise serializers.ValidationError(
                _("Task `{name}` can not be canceled.").format(name=task.name)
            )
        return task


class ChangeBehandelaarTasksSerializer(serializers.Serializer):
    zaak = serializers.URLField(
        help_text=_("URL-reference to the ZAAK in its API"),
    )
    rol = serializers.URLField(help_text=_("URL-reference to the ROL in its API"))

    def validate_zaak(self, zaak) -> Zaak:
        try:
            zaak = get_zaak(zaak_url=zaak)
        except (ClientError, HTTPError) as exc:
            raise serializers.ValidationError(_("ZAAK was not found."))
        return zaak

    def validate_rol(self, rol) -> Rol:
        try:
            rol = fetch_rol(rol)
        except (ClientError, HTTPError) as exc:
            raise serializers.ValidationError(detail=str(exc))
        return rol

    def perform(self):
        assert self.is_valid(), "Serializer must be valid"

        # Get camunda tasks associated to this zaak
        change_assignee_tasks = []
        process_instances = get_top_level_process_instances(
            self.validated_data["zaak"].url, exclude_zaak_creation=True
        )
        for pi in process_instances:
            for task in pi.tasks:
                if task.name.lower() not in ["adviseren", "accorderen"]:
                    change_assignee_tasks.append(
                        {
                            "task_id": task.id,
                            "assignee": self.validated_data[
                                "rol"
                            ].betrokkene_identificatie["identificatie"],
                        }
                    )

        new_rol = {
            "betrokkeneType": self.validated_data["rol"].betrokkene_type,
            "betrokkeneIdentificatie": self.validated_data[
                "rol"
            ].betrokkene_identificatie,
            "name": self.validated_data["rol"].get_name(),
            "omschrijving": self.validated_data["rol"].get_roltype_omschrijving(),
            "roltoelichting": self.validated_data["rol"].get_roltype_omschrijving(),
            "identificatie": self.validated_data["rol"].get_identificatie(),
        }

        with parallel(max_workers=settings.MAX_WORKERS) as executor:
            # Update 'behandelaar' variable
            list(
                executor.map(
                    lambda var: update_process_instance_variable(**var),
                    [
                        {
                            "pid": pid.id,
                            "variable_name": "behandelaar",
                            "variable_value": self.validated_data[
                                "rol"
                            ].betrokkene_identificatie["identificatie"],
                        }
                        for pid in process_instances
                    ],
                )
            )

            if self.validated_data["rol"].omschrijving == "Hoofdbehandelaar":
                # Update `initiator` variable
                list(
                    executor.map(
                        lambda var: update_process_instance_variable(**var),
                        [
                            {
                                "pid": pid.id,
                                "variable_name": "initiator",
                                "variable_value": self.validated_data[
                                    "rol"
                                ].betrokkene_identificatie["identificatie"],
                            }
                            for pid in process_instances
                        ],
                    )
                )
            # Update rol variable
            list(
                executor.map(
                    lambda var: update_process_instance_variable(**var),
                    [
                        {
                            "pid": pid.id,
                            "variable_name": self.validated_data[
                                "rol"
                            ].get_roltype_omschrijving(),
                            "variable_value": new_rol,
                        }
                        for pid in process_instances
                    ],
                )
            )
            # Change assignee of tasks to match new behandelaar
            list(
                executor.map(
                    lambda task_and_assignee: set_assignee(**task_and_assignee),
                    change_assignee_tasks,
                )
            )


class CountCamundaUserTasks(serializers.Serializer):
    count = serializers.IntegerField(
        min_value=0,
        required=True,
        help_text=_("Count of open camunda user tasks for user."),
    )
