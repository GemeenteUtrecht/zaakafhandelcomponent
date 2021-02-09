import uuid

from django.utils.translation import gettext_lazy as _

from django_camunda.api import complete_task, send_message
from drf_spectacular.openapi import OpenApiParameter, OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from zac.core.camunda import get_process_zaak_url
from zac.core.services import get_zaak

from ..data import Task
from ..dynamic_forms.context import build_dynamic_form_serializer
from ..messages import get_messages
from ..process_instances import get_process_instance
from ..processes import get_process_instances
from ..user_tasks import UserTaskData, get_context, get_task
from .permissions import CanPerformTasks, CanSendMessages
from .serializers import (
    ErrorSerializer,
    MessageSerializer,
    ProcessInstanceSerializer,
    UserTaskSerializer,
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


class UserTaskView(APIView):  # change into -> UserTaskView
    """
    Get the user task context from Camunda and perform the user task on Camunda.

    Given the task ID, retrieve the task details from Camunda and enrich this with
    context for the UI. The shape of the context depends on the ``form`` value.

    The shape of the payload of the user task depends on the ``form`` value as well.
    """

    # TODO: check permissions that user is allowed to execute process task stuff.
    # See https://github.com/GemeenteUtrecht/zaakafhandelcomponent/blob/9b7ea9cbab66c7356e7417b6ce98245272954e1c/backend/src/zac/core/api/permissions.py#L69  # noqa
    # for a first pass
    permission_classes = (permissions.IsAuthenticated & CanPerformTasks,)
    serializer_class = UserTaskSerializer

    def get_object(self) -> Task:
        task = get_task(self.kwargs["task_id"], check_history=False)
        if task is None:
            raise exceptions.NotFound(
                _("The task with given task ID does not exist (anymore).")
            )
        # May raise a permission denied
        self.check_object_permissions(self.request, task)
        return task

    def get_serializer(self, **kwargs):
        return self.serializer_class(**kwargs)

    @extend_schema(
        summary=_("Retrieve user task data and context"),
        responses={
            200: UserTaskSerializer,
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
        request=OpenApiTypes.OBJECT,
        responses={
            200: OpenApiTypes.OBJECT,
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
        # TODO: properly abstract away with Daniël's work
        serializer = self.get_serializer(
            data={
                **request.data,
                "form": task.form,
            },
            context={"task": task},
        )
        serializer.is_valid(raise_exception=True)

        variables = {
            **get_bptl_app_id_variable(),
            **serializer.get_process_variables(),
        }

        complete_task(task.id, variables)

        return Response(serializer.data)


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


class PerformTaskView(APIView):
    """
    Implement polymorphic(?) perform task view
    """

    pass
