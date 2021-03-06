import uuid

from django.utils.translation import gettext_lazy as _

from django_camunda.api import complete_task, send_message
from django_camunda.client import get_client
from drf_spectacular.openapi import OpenApiParameter, OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from zac.accounts.models import User
from zac.core.camunda import get_process_zaak_url
from zac.core.services import _client_from_url, fetch_zaaktype, get_roltypen, get_zaak
from zgw.models import Zaak

from ..data import Task
from ..messages import get_messages
from ..process_instances import get_process_instance
from ..processes import get_process_instances
from ..user_tasks import UserTaskData, get_context, get_registry_item, get_task
from .permissions import CanPerformTasks, CanSendMessages
from .serializers import (
    ErrorSerializer,
    MessageSerializer,
    ProcessInstanceSerializer,
    SetTaskAssigneeSerializer,
    SubmitUserTaskSerializer,
    UserTaskContextSerializer,
)
from .utils import get_bptl_app_id_variable


class ProcessInstanceFetchView(APIView):
    schema_summary = _("List process instances for a zaak")
    serializer_class = ProcessInstanceSerializer

    @extend_schema(
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
        Get the Camunda process instances for a given zaak.

        Retrieve the process instances where the zaak URL is matches the process
        `zaakUrl` variable. Process instances return the available message that can be
        sent into the process and the available user tasks. The response includes the
        child-process instances of each matching process instance.
        """
        zaak_url = request.GET.get("zaak_url")
        if not zaak_url:
            err_serializer = ErrorSerializer(data={"detail": "missing zaak_url"})
            return Response(err_serializer.data, status=status.HTTP_400_BAD_REQUEST)

        process_instances = get_process_instances(zaak_url)
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
                    _("The task with given task ID does not exist (anymore).")
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
        summary=_("Retrieve user task data and context"),
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
        summary=_("Submit user task data"),
        request=SubmitUserTaskSerializer,
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
        process variables are set.

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
        summary=_("Send BPMN message"),
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

    def _create_rol(self, zaak: Zaak, user: User):
        # fetch roltype
        roltypen = get_roltypen(zaak.zaaktype, omschrijving_generiek="behandelaar")
        if not roltypen:
            return
        roltype = roltypen[0]

        zrc_client = _client_from_url(zaak.url)
        voorletters = " ".join([part[0] for part in user.first_name.split()])

        # check if the betrokkene already exists
        existing = zrc_client.list(
            "rol",
            query_params={
                "zaak": zaak.url,
                "betrokkeneIdentificatie__medewerker__identificatie": user.username,
            },
        )
        if existing["count"]:
            return

        data = {
            "zaak": zaak.url,
            "betrokkeneType": "medewerker",
            "roltype": roltype.url,
            "roltoelichting": "task claiming",
            "betrokkeneIdentificatie": {
                "identificatie": user.username,
                "achternaam": user.last_name,
                "voorletters": voorletters,
            },
        }
        zrc_client.create("rol", data)

    @extend_schema(
        summary=_("Set task assignee or delegate"),
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
            assignee = User.objects.get(username=assignee)
            camunda_client.post(
                f"task/{task.id}/assignee",
                json={"userId": assignee.username},
            )
            self._create_rol(zaak, assignee)

        # If delegate is given, set delegate.
        delegate = serializer.validated_data["delegate"]
        if delegate:
            delegate = User.objects.get(username=delegate)
            camunda_client.post(
                f"task/{task.id}/delegate",
                json={"userId": delegate.username},
            )
            self._create_rol(zaak, delegate)

        return Response(status=status.HTTP_204_NO_CONTENT)
