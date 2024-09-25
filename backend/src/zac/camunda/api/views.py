import uuid
from typing import Any, Dict, Iterable, Optional

from django.utils.translation import gettext_lazy as _

from django_camunda.client import get_client
from django_camunda.types import CamundaId
from django_camunda.utils import deserialize_variable, serialize_variable
from django_filters.utils import translate_validation
from drf_spectacular.openapi import OpenApiParameter, OpenApiTypes
from drf_spectacular.utils import extend_schema
from requests.exceptions import HTTPError
from rest_framework import exceptions, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from zgw_consumers.api_models.constants import RolOmschrijving, RolTypes

from zac.accounts.models import User
from zac.camunda.api.utils import get_bptl_app_id_variable
from zac.camunda.constants import AssigneeTypeChoices
from zac.camunda.data import Task
from zac.camunda.messages import get_messages, get_process_instances_messages_for_zaak
from zac.camunda.process_instances import (
    get_process_instance,
    get_top_level_process_instances,
)
from zac.camunda.user_tasks import (
    UserTaskData,
    get_context,
    get_registry_item,
    get_task,
)
from zac.camunda.user_tasks.api import (
    cancel_activity_instance_of_task,
    get_camunda_user_task_count,
    get_camunda_user_tasks_for_zaak,
    get_killable_camunda_tasks,
    set_assignee,
    set_assignee_and_complete_task,
)
from zac.core.api.permissions import CanCreateZaken, CanReadZaken
from zac.core.api.serializers import ZaakSerializer
from zac.core.camunda.utils import get_process_zaak_url, resolve_assignee
from zac.core.services import client_from_url, fetch_zaaktype, get_roltypen, get_zaak
from zgw.models import Zaak

from ..user_tasks.history import get_camunda_history_for_zaak
from .filters import CamundaFilterSet, zaakUrlFilterSet
from .permissions import CanPerformTasks, CanSendMessages
from .serializers import (
    BPMNSerializer,
    CancelTaskSerializer,
    ChangeBehandelaarTasksSerializer,
    CountCamundaUserTasks,
    CreateZaakRedirectCheckSerializer,
    ErrorSerializer,
    HistoricUserTaskSerializer,
    MessageSerializer,
    MessageVariablesSerializer,
    ProcessInstanceMessageSerializer,
    ProcessInstanceSerializer,
    SetTaskAssigneeSerializer,
    SubmitUserTaskSerializer,
    TaskSerializer,
    UserTaskContextSerializer,
)
from .utils import get_bptl_app_id_variable


class ProcessInstanceFetchView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProcessInstanceSerializer
    filterset_class = CamundaFilterSet

    @extend_schema(
        summary=_("List process instances for a ZAAK."),
        parameters=[
            OpenApiParameter(
                "zaakUrl",
                OpenApiTypes.URI,
                OpenApiParameter.QUERY,
                required=True,
            ),
            OpenApiParameter(
                "includeBijdragezaak",
                OpenApiTypes.BOOL,
                OpenApiParameter.QUERY,
                default=False,
                required=False,
            ),
            OpenApiParameter(
                "excludeZaakCreation",
                OpenApiTypes.BOOL,
                OpenApiParameter.QUERY,
                default=True,
                required=False,
            ),
        ],
        responses={
            200: serializer_class(many=True),
            400: ErrorSerializer,
        },
    )
    def get(self, request: Request, *args, **kwargs):
        """
        Get the Camunda process instances for a given ZAAK.

        Retrieve the process instances where the ZAAK-URL matches the process
        `zaakUrl` variable. Process instances return the available message that can be
        sent into the process and the available user tasks. The response includes the
        child-process instances of each matching process instance.

        """

        filterset = self.filterset_class(
            data=self.request.query_params, request=self.request
        )
        filterset.is_valid(raise_exception=True)

        process_instances = get_top_level_process_instances(
            filterset.serializer.validated_data["zaakUrl"],
            include_bijdragezaak=filterset.serializer.validated_data[
                "includeBijdragezaak"
            ],
            exclude_zaak_creation=filterset.serializer.validated_data[
                "excludeZaakCreation"
            ],
        )
        # Exclude
        serializer = self.serializer_class(
            process_instances,
            many=True,
            context={"killable_tasks": get_killable_camunda_tasks()},
        )

        return Response(serializer.data)


class FetchTaskView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = TaskSerializer
    filterset_class = CamundaFilterSet

    @extend_schema(
        summary=_("List tasks for a ZAAK."),
        parameters=[
            OpenApiParameter(
                "zaakUrl",
                OpenApiTypes.URI,
                OpenApiParameter.QUERY,
                required=True,
            ),
            OpenApiParameter(
                "excludeZaakCreation",
                OpenApiTypes.BOOL,
                OpenApiParameter.QUERY,
                default=True,
            ),
        ],
        responses={
            200: serializer_class(many=True),
            400: ErrorSerializer,
        },
    )
    def get(self, request: Request, *args, **kwargs):
        """
        Get the camunda user tasks for a given ZAAK.

        Retrieve the tasks where the ZAAK-URL matches the process
        `zaakUrl` variable.

        """

        filterset = self.filterset_class(
            data=self.request.query_params, request=self.request
        )
        filterset.is_valid(raise_exception=True)

        tasks = get_camunda_user_tasks_for_zaak(
            zaak_url=filterset.data["zaakUrl"],
            exclude_zaak_creation=True,
        )
        serializer = self.serializer_class(tasks, many=True)

        return Response(serializer.data)


class ProcessInstanceMessagesView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProcessInstanceMessageSerializer
    filterset_class = CamundaFilterSet

    @extend_schema(
        summary=_("List messages for a ZAAK."),
        parameters=[
            OpenApiParameter(
                "zaakUrl",
                OpenApiTypes.URI,
                OpenApiParameter.QUERY,
                required=True,
            ),
        ],
        responses={
            200: serializer_class(many=True),
            400: ErrorSerializer,
        },
    )
    def get(self, request: Request, *args, **kwargs):
        """
        Get the Camunda messages for a given ZAAK.

        Retrieve the messages related to the root process instance where
        the ZAAK-URL matches the process `zaakUrl` variable.

        """

        filterset = self.filterset_class(
            data=self.request.query_params, request=self.request
        )
        if not filterset.is_valid():
            raise exceptions.ValidationError(filterset.errors)
        process_instances = get_process_instances_messages_for_zaak(
            zaak_url=filterset.serializer.validated_data["zaakUrl"],
        )
        serializer = self.serializer_class(process_instances, many=True)

        return Response(serializer.data)


class CreateZaakRedirectCheckView(APIView):
    permission_classes = (permissions.IsAuthenticated, CanCreateZaken)
    serializer_class = CreateZaakRedirectCheckSerializer

    @extend_schema(
        summary=_("Retrieve camunda variable for process instance."),
        parameters=[
            OpenApiParameter(
                name="id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                required=True,
                description="UUID of process instance",
            ),
        ],
        responses={200: ZaakSerializer},
    )
    def get(self, request: Request, id: uuid.UUID):
        serializer = self.serializer_class(data={"id": id})
        serializer.is_valid(raise_exception=True)

        zaak = get_zaak(zaak_url=serializer.validated_data["zaak"])
        serializer = ZaakSerializer(instance=zaak)
        return Response(serializer.data)


class UserTaskView(APIView):
    """
    Get the user task context from Camunda and perform the user task on Camunda.

    Given the task ID, retrieve the task details from Camunda and enrich this with
    context for the UI. The shape of the context depends on the ``form`` value.
    """

    permission_classes = (permissions.IsAuthenticated & CanPerformTasks,)

    def get_object(self) -> Task:
        if not hasattr(self, "_task"):
            task = get_task(self.kwargs["task_id"], check_history=False)
            if task is None:
                raise exceptions.NotFound(
                    _("The task with given task `id` does not exist (anymore).")
                )
            self._task = task
        return self._task

    def get_serializer(self, **kwargs):
        mapping = {
            "PUT": SubmitUserTaskSerializer,
            "GET": UserTaskContextSerializer,
        }
        return mapping[self.request.method](**kwargs)

    def get_parsers(self):
        default = super().get_parsers()
        if getattr(
            self, "swagger_fake_view", False
        ):  # hit during api schema generation
            return default

        task = self.get_object()
        item = get_registry_item(task)
        if not item.parsers:
            return default
        return [parser() for parser in item.parsers]

    def get_renderers(self):
        default = super().get_renderers()
        if getattr(
            self, "swagger_fake_view", False
        ):  # hit during api schema generation
            return default

        task = self.get_object()
        item = get_registry_item(task)
        if not item.renderers:
            return default
        return [renderer() for renderer in item.renderers]

    @extend_schema(
        summary=_("Retrieve user task data and context."),
        responses={
            200: UserTaskContextSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
        },
    )
    def get(self, request: Request, task_id: uuid.UUID):
        task = self.get_object()
        task_data = UserTaskData(task=task, context=get_context(task))
        serializer = self.get_serializer(
            instance=task_data,
            context={
                "request": request,
                "view": self,
                "killable_tasks": get_killable_camunda_tasks(),
            },
        )
        return Response(serializer.data)

    @extend_schema(
        summary=_("Submit user task data."),
        responses={
            204: None,
            400: OpenApiTypes.OBJECT,
            403: ErrorSerializer,
            404: ErrorSerializer,
            500: ErrorSerializer,
        },
    )
    def put(self, request: Request, task_id: uuid.UUID):
        """
        Submit user task data for Camunda user tasks.

        The exact shape of the data depends on the Camunda task type. On succesful,
        valid submission, the user task in Camunda is completed and the resulting
        process variables are set. The final assignee of the user task is also set
        for history trail purposes.

        The ZAC always injects its own ``bptlAppId`` process variable so that BPTL
        executes tasks from the right context.

        This endpoint is only available if you have permissions to perform user tasks.
        """
        task = self.get_object()
        serializer = self.get_serializer(
            data={
                **request.data,
                "form": task.form_key,
            },
            context={"task": task, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.on_task_submission()
        variables = {
            **get_bptl_app_id_variable(),
            **serializer.get_process_variables(),
        }

        user_assignee = f"{AssigneeTypeChoices.user}:{request.user}"

        # For case history purposes set assignee if no assignee is set yet, has changed or the assignee is a group.
        set_assignee_and_complete_task(task, user_assignee, variables=variables)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SendMessageView(APIView):
    permission_classes = (permissions.IsAuthenticated & CanSendMessages,)
    serializer_class = MessageSerializer

    def get_serializer(self, **kwargs):
        serializer = self.serializer_class(**kwargs)
        process_instance_id = serializer.initial_data.get("process_instance_id", None)

        # no (valid) process instance ID -> get a serializer with no valid messages -> invalid
        # POST request
        if not process_instance_id:
            return serializer

        # set the valid process instance messages _if_ a process instance exists
        process_instance = get_process_instance(process_instance_id)
        if process_instance is None or process_instance.historical:
            return serializer

        messages = get_messages(process_instance.definition_id)
        serializer.set_message_choices(messages)

        return serializer

    @extend_schema(
        summary=_("Send BPMN message."),
        description=_(
            "Sets the messageAssignee to the user making the request and the bptlAppId variable."
        ),
        request=MessageSerializer,
        responses={
            201: MessageVariablesSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Send a BPMN message into a running process instance.

        Typically this will start an embedded sub process in the running process
        instance.

        Note that the available/valid messages depend on the specific process
        definition and are validated at run-time.

        """
        # First populate message choices from the process instance...
        serializer = self.get_serializer(data=request.data)
        # ... then validate.
        serializer.is_valid(raise_exception=True)

        # Check permissions
        process_instance_id = serializer.validated_data["process_instance_id"]
        process_instance = get_process_instance(process_instance_id)
        zaak_url = get_process_zaak_url(process_instance)
        zaak = get_zaak(zaak_url=zaak_url)
        self.check_object_permissions(request, zaak)

        # Set variables
        variables = get_bptl_app_id_variable()
        variables["messageAssignee"] = f"{AssigneeTypeChoices.user}:{request.user}"

        def _send_message(
            name: str,
            process_instance_ids: Iterable[CamundaId],
            variables: Optional[Dict[str, Any]] = None,
            result_enabled=False,
        ) -> None:
            """
            Taken from django_camunda and adapted for Camunda 7.11 and higher.

            Send a BPMN message into running process instances, with optional process variables.

            :param name: Name/ID of the message definition, extract this from the process.
            :param process_instance_ids: an iterable of process instance IDs, can be uuid
            instances or strings.
            :param variables: Optional mapping of ``{name: value}`` process variables. Will be
            serialized as part of the message sending.
            """
            client = get_client()
            variables = (
                {name: serialize_variable(value) for name, value in variables.items()}
                if variables
                else None
            )
            for instance_id in process_instance_ids:
                body = {
                    "messageName": name,
                    "processInstanceId": instance_id,
                    "processVariables": variables or {},
                    "resultEnabled": result_enabled,
                    "variablesInResultEnabled": result_enabled,
                }
                return client.post("message", json=body)

        results = _send_message(
            serializer.validated_data["message"],
            [process_instance.id],
            variables,
            result_enabled=True,
        )

        # In our case messages always correlate to a single definition, hence we can grab results[0] or crash if something isn't right.
        return Response(
            MessageVariablesSerializer(
                {
                    key: deserialize_variable(val)
                    for key, val in results[0]["variables"].items()
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )


class ChangeBehandelaarTasksView(APIView):
    permission_classes = (permissions.IsAuthenticated & CanPerformTasks,)
    serializer_class = ChangeBehandelaarTasksSerializer

    @extend_schema(
        summary=_("Change camunda behandelaar."),
        request=ChangeBehandelaarTasksSerializer,
        responses={
            204: None,
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Changes the assignee from all tasks where the assignee is a behandelaar.
        It also changes the `initiator`, `behandelaar` and `roltype.omschrijving` variables in all process instances
        related to the zaak if relevant.

        In the current implementation we do not adjust kownsl review requests.

        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.perform()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SetTaskAssigneeView(APIView):
    permission_classes = (permissions.IsAuthenticated & CanPerformTasks,)
    serializer_class = SetTaskAssigneeSerializer

    def _create_rol(self, zaak: Zaak, name: str) -> None:
        user = resolve_assignee(name)
        if not isinstance(user, User):
            return

        # fetch roltype
        roltypen = get_roltypen(
            zaak.zaaktype, omschrijving_generiek=RolOmschrijving.behandelaar
        )
        if not roltypen:
            return
        roltype = roltypen[0]

        zrc_client = client_from_url(zaak.url)

        betrokkene_identificatie = {
            "identificatie": f"{AssigneeTypeChoices.user}:{user}",
            "achternaam": user.last_name.capitalize(),
            "voorletters": "".join(
                [part[0].upper() + "." for part in user.first_name.split()]
            ).strip(),
        }

        # check if the betrokkene already exists
        existing = zrc_client.list(
            "rol",
            query_params={
                "zaak": zaak.url,
                "betrokkeneIdentificatie__medewerker__identificatie": betrokkene_identificatie[
                    "identificatie"
                ],
            },
        )
        if existing["count"]:
            return

        data = {
            "zaak": zaak.url,
            "betrokkeneType": RolTypes.medewerker,
            "roltype": roltype.url,
            "roltoelichting": roltype.omschrijving,
            "betrokkeneIdentificatie": betrokkene_identificatie,
        }
        zrc_client.create("rol", data)

    @extend_schema(
        summary=_("Set task assignee or delegate."),
        responses={
            204: None,
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = serializer.validated_data["task"]
        process_instance = get_process_instance(task.process_instance_id)
        zaak_url = get_process_zaak_url(process_instance)
        zaak = get_zaak(zaak_url=zaak_url)
        self.check_object_permissions(request, zaak)
        zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)

        camunda_client = get_client()

        # If assignee is given, set assignee.
        assignee = serializer.validated_data["assignee"]
        if assignee:
            set_assignee(task.id, assignee)

        # If delegate is given, set delegate.
        delegate = serializer.validated_data["delegate"]
        if delegate:
            camunda_client.post(
                f"task/{task.id}/delegate",
                json={"userId": delegate},
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class GetBPMNView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = BPMNSerializer

    @extend_schema(
        summary=_("Retrieve the XML of the BPMN."),
        responses={
            200: BPMNSerializer,
        },
    )
    def get(self, request, *args, **kwargs):
        client = get_client()
        process_definition_id = kwargs["process_definition_id"]
        try:
            response = client.get(f"process-definition/{process_definition_id}/xml")
            serializer = self.serializer_class(data=response)
            serializer.is_valid(raise_exception=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except HTTPError as exc:
            if exc.response.status_code == 400:
                raise exceptions.ValidationError(exc.response.json())
            raise


class UserTaskHistoryView(APIView):
    permission_classes = (permissions.IsAuthenticated & CanReadZaken,)
    filterset_class = zaakUrlFilterSet

    def get_serializer(self, **kwargs):
        return HistoricUserTaskSerializer(**kwargs)

    @extend_schema(
        summary=_("Retrieve the historical user task data of the ZAAK."),
        description=_(
            "User tasks are reverse sorted on the `created` key. The history array is sorted alphabetically on the `variable_name` key."
        ),
        parameters=[
            OpenApiParameter(
                "zaakUrl",
                OpenApiTypes.URI,
                OpenApiParameter.QUERY,
                required=True,
            )
        ],
    )
    def get(self, request, *args, **kwargs):
        filterset = self.filterset_class(
            data=self.request.query_params, request=self.request
        )
        filterset.is_valid(raise_exception=True)
        zaak_url = filterset.data["zaakUrl"]
        user_task_history = get_camunda_history_for_zaak(zaak_url)
        user_task_history.sort(key=lambda obj: obj.task.created, reverse=True)
        serializer = self.get_serializer(instance=user_task_history, many=True)
        return Response(serializer.data)


class CancelTaskView(APIView):
    permission_classes = (
        permissions.IsAuthenticated,
        CanPerformTasks,
    )

    def get_serializer(self, **kwargs):
        return CancelTaskSerializer(**kwargs)

    @extend_schema(
        summary=_("Cancel a camunda user task of the ZAAK."),
        description=_(
            "Allows a user to cancel the camunda task after it has been (accidentally) created."
        ),
        responses={204: None},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = serializer.validated_data["task"]
        zaak_url = task.get_variable("zaakUrl")
        zaak = get_zaak(zaak_url=zaak_url)
        self.check_object_permissions(request, zaak)
        cancel_activity_instance_of_task(task)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserTaskCountView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer(self, *args, **kwargs):
        return CountCamundaUserTasks(*args, **kwargs)

    @extend_schema(
        summary=_("Retrieve number of open camunda user tasks for user."), request=None
    )
    def post(self, request, *args, **kwargs):
        assignees = [f"{AssigneeTypeChoices.user}:{request.user}"]
        count = get_camunda_user_task_count(assignees)
        serializer = self.get_serializer({"count": count})
        return Response(serializer.data)
