import uuid

from django.utils.translation import gettext_lazy as _

from django_camunda.api import complete_task, send_message
from drf_spectacular.openapi import OpenApiParameter, OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from zgw_consumers.api_models.zaken import Zaak

from zac.core.camunda import get_process_zaak_url
from zac.core.services import _client_from_url, get_zaak

from ..data import Task
from ..messages import get_messages
from ..process_instances import get_process_instance
from ..processes import get_process_instances
from ..user_tasks import UserTaskData, get_context, get_task
from .permissions import CanPerformTasks
from .serializers import (
    ErrorSerializer,
    ProcessInstanceSerializer,
    UserTaskContextSerializer,
    MessageSerializer,
)


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


class GetTaskContextView(APIView):
    """
    Retrieve the user task context from Camunda.

    Given the task ID, retrieve the task details from Camunda and enrich this with
    context for the UI. The shape of the context depends on the ``form`` value.
    """

    # TODO: check permissions that user is allowed to execute process task stuff.
    # See https://github.com/GemeenteUtrecht/zaakafhandelcomponent/blob/9b7ea9cbab66c7356e7417b6ce98245272954e1c/backend/src/zac/core/api/permissions.py#L69  # noqa
    # for a first pass
    permission_classes = (permissions.IsAuthenticated & CanPerformTasks,)
    serializer_class = UserTaskContextSerializer
    schema_summary = _("Retrieve user task data and context")

    @extend_schema(
        responses={
            200: UserTaskContextSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
        }
    )
    def get(self, request: Request, task_id: uuid.UUID):
        task = self.get_object()
        task_data = UserTaskData(task=task, context=get_context(task))
        serializer = self.serializer_class(
            instance=task_data,
            context={"request": request, "view": self},
        )
        return Response(serializer.data)

    def get_object(self) -> Task:
        task = get_task(self.kwargs["task_id"], check_history=False)
        if task is None:
            raise exceptions.NotFound(
                _("The task with given task ID does not exist (anymore).")
            )
        # May raise a permission denied
        self.check_object_permissions(self.request, task)
        return task
        

class SendMessageView(APIView):
    permission_classes = (permissions.IsAuthenticated & CanPerformTasks,)
    serializer_class = MessageSerializer

    def get_serializer(self, **kwargs):
        serializer = super().get_serializer(**kwargs)
        process_instance_id = serializer.data.get("process_instance_id")

        # no (valid) process instance ID -> get a form with no valid messages -> invalid
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

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # check permissions
        process_instance_id = serializer.validated_data["process_instance_id"]
        process_instance = get_process_instance(process_instance_id)

        zaak_url = get_process_zaak_url(get_process_instance)
        zaak = get_zaak(zaak_url=zaak_url)
        self.check_object_permissions(request, zaak)

        # build service variables to continue execution
        zrc_client = _client_from_url(zaak.url)
        ztc_client = _client_from_url(zaak.zaaktype)

        zrc_jwt = zrc_client.auth.credentials()["Authorization"]
        ztc_jwt = ztc_client.auth.credentials()["Authorization"]

        variables = {
            "services": {
                "zrc": {"jwt": zrc_jwt},
                "ztc": {"jwt": ztc_jwt},
            },
        }

        send_message(serializer.cleaned_data["message"], [process_instance.id], variables)
        return Response(status=status.HTTP_201_CREATED)


class PerformTaskView(APIView):
    permission_classes = (permissions.IsAuthenticated & CanPerformTasks,)
    check_task_history = False

    def _get_task(self, refresh=False) -> Task:
        if not hasattr(self, "_task") or refresh:
            task = get_task(
                self.kwargs["task_id"], check_history=self.check_task_history
            )
            if task is None:
                raise Http404("No such task")
            self._task = task
        return self._task

    def _get_zaak(self, request: Request) -> Zaak:
        task = self._get_task()
        process_instance = get_process_instance(self._task.process_instance_id)

        zaak_url = get_process_zaak_url(process_instance)
        zaak = get_zaak(zaak_url=zaak_url)
        zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)
        
        # Check permissions on zaak
        self.check_object_permissions(request, zaak)
        return zaak

    def get(self, request, *args, **kwargs):
        zaak = self._get_zaak(request)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        zaak = self._get_zaak(request)

        zrc_client = _client_from_url(zaak.url)
        ztc_client = _client_from_url(zaak.zaaktype.url)

        zrc_jwt = zrc_client.auth.credentials()["Authorization"]
        ztc_jwt = ztc_client.auth.credentials()["Authorization"]

        services = {
            "zrc": {"jwt": zrc_jwt},
            "ztc": {"jwt": ztc_jwt},
        }

        variables = {
            "services": services,
            **form.get_process_variables(),
        }

        complete_task(self._task.id, variables)