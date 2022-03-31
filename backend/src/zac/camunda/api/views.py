import uuid

from django.utils.translation import gettext_lazy as _

from django_camunda.api import complete_task, send_message
from django_camunda.client import get_client
from drf_spectacular.openapi import OpenApiParameter, OpenApiTypes
from drf_spectacular.utils import extend_schema
from requests.exceptions import HTTPError
from rest_framework import exceptions, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from zac.accounts.models import User
from zac.camunda.constants import AssigneeTypeChoices
from zac.core.api.permissions import CanReadZaken
from zac.core.camunda import get_process_zaak_url
from zac.core.services import _client_from_url, fetch_zaaktype, get_roltypen, get_zaak
from zgw.models import Zaak

from ..data import Task
from ..messages import get_messages
from ..process_instances import get_process_instance
from ..processes import get_top_level_process_instances
from ..user_tasks import UserTaskData, get_context, get_registry_item, get_task
from ..user_tasks.api import cancel_activity_instance_of_task
from ..user_tasks.history import get_camunda_history_for_zaak
from .permissions import CanPerformTasks, CanSendMessages
from .serializers import (
    BPMNSerializer,
    CancelTaskSerializer,
    ErrorSerializer,
    HistoricUserTaskSerializer,
    MessageSerializer,
    ProcessInstanceSerializer,
    SetTaskAssigneeSerializer,
    SubmitUserTaskSerializer,
    UserTaskContextSerializer,
)
from .utils import get_bptl_app_id_variable


class ProcessInstanceFetchView(APIView):
    serializer_class = ProcessInstanceSerializer

    @extend_schema(
        summary=_("List process instances for a ZAAK."),
        parameters=[
            OpenApiParameter(
                "zaak_url",
                OpenApiTypes.URI,
                OpenApiParameter.QUERY,
                required=True,
            )
        ],
        responses={
            200: serializer_class(many=True),
            400: ErrorSerializer,
        },
    )
    def get(self, request: Request, *args, **kwargs):
        """
        Get the Camunda process instances for a given ZAAK.

        Retrieve the process instances where the ZAAK-URL is matches the process
        `zaakUrl` variable. Process instances return the available message that can be
        sent into the process and the available user tasks. The response includes the
        child-process instances of each matching process instance.
        """
        zaak_url = request.GET.get("zaak_url")
        if not zaak_url:
            err_serializer = ErrorSerializer({"detail": "missing zaak_url"})
            return Response(err_serializer.data, status=status.HTTP_400_BAD_REQUEST)

        process_instances = get_top_level_process_instances(zaak_url)
        serializer = self.serializer_class(process_instances, many=True)

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
            context={"request": request, "view": self},
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

        # For case history purposes set assignee if no assignee is set yet, has changed or the assignee is a group.
        if (
            not task.assignee
            or task.assignee != f"{AssigneeTypeChoices.user}:{request.user}"
            or task.assignee_type == AssigneeTypeChoices.group
        ):
            camunda_client = get_client()
            assignee = f"{AssigneeTypeChoices.user}:{request.user}"
            camunda_client.post(
                f"task/{task.id}/assignee",
                json={"userId": assignee},
            )

        complete_task(task.id, variables)
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
        request=MessageSerializer,
        responses={
            204: None,
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

        send_message(
            serializer.validated_data["message"],
            [process_instance.id],
            variables,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class SetTaskAssigneeView(APIView):
    permission_classes = (permissions.IsAuthenticated & CanPerformTasks,)
    serializer_class = SetTaskAssigneeSerializer

    def _create_rol(self, zaak: Zaak, name: str) -> None:
        user_or_group, _name = name.split(":", 1)
        if user_or_group == AssigneeTypeChoices.group:
            return

        # fetch roltype
        roltypen = get_roltypen(zaak.zaaktype, omschrijving_generiek="behandelaar")
        if not roltypen:
            return
        roltype = roltypen[0]

        zrc_client = _client_from_url(zaak.url)

        user = User.objects.get(username=_name)

        betrokkene_identificatie = {
            "identificatie": user.username,
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
            "betrokkeneType": "medewerker",
            "roltype": roltype.url,
            "roltoelichting": "task claiming",
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
            camunda_client.post(
                f"task/{task.id}/assignee",
                json={"userId": assignee},
            )
            self._create_rol(zaak, assignee)

        # If delegate is given, set delegate.
        delegate = serializer.validated_data["delegate"]
        if delegate:
            camunda_client.post(
                f"task/{task.id}/delegate",
                json={"userId": delegate},
            )
            self._create_rol(zaak, delegate)

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

    def get_serializer(self, **kwargs):
        return HistoricUserTaskSerializer(**kwargs)

    @extend_schema(
        summary=_("Retrieve the historical user task data of the ZAAK."),
        description=_(
            "User tasks are reverse sorted on the `created` key. The history array is sorted alphabetically on the `variable_name` key."
        ),
        parameters=[
            OpenApiParameter(
                "zaak_url",
                OpenApiTypes.URI,
                OpenApiParameter.QUERY,
                required=True,
            )
        ],
    )
    def get(self, request, *args, **kwargs):
        zaak_url = request.GET.get("zaak_url")
        if not zaak_url:
            raise exceptions.ValidationError(
                _("Missing the `zaak_url` query parameter.")
            )

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
