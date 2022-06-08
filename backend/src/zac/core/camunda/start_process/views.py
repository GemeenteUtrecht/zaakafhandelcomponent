import uuid

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.src.zac.core.api.views import GetZaakMixin
from zac.camunda.api.utils import get_bptl_app_id_variable, start_process
from zac.camunda.process_instances import delete_process_instance
from zac.camunda.processes import get_process_definitions, get_process_instances

# Create your views here.


class StartCamundaProcessView(GetZaakMixin, APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = StartCamundaProcessSerializer

    def get_serializer(self, request, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    def post(
        self, request: Request, bronorganisatie: str, identificatie: str
    ) -> Response:
        zaak = self.get_object()

        # First check if there is still a CREATE_ZAAK_PROCESS_DEFINITION_KEY process that needs to be cleaned up.
        process_instances = get_process_instances(zaak.url)
        if process_instances:
            pdefinition_to_pinstance_map = {
                pi.definition_id: pid
                for pid, pi in process_instances.items()
                if pi.definition_id
            }
            process_definitions = get_process_definitions(
                pdefinition_to_pinstance_map.keys()
            )

            p_def_id_to_key_map = {}
            for pdef in process_definitions:
                if pdef.key in p_def_id_to_key_map:
                    p_def_id_to_key_map[pdef.key].append(pdef.id)
                else:
                    p_def_id_to_key_map[pdef.key] = [pdef.id]

            if (
                settings.CREATE_ZAAK_PROCESS_DEFINITION_KEY
                in p_def_id_to_key_map.keys()
            ):
                pdef_id = p_def_id_to_key_map[
                    settings.CREATE_ZAAK_PROCESS_DEFINITION_KEY
                ]
                if pdef_id in pdefinition_to_pinstance_map.keys():
                    delete_pid = pdefinition_to_pinstance_map[pdef_id]
                    delete_process_instance(delete_pid)

        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        details = start_process(
            process_key=settings.START_CAMUNDA_PROCESS_DEFINITION_KEY,
            variables=serializer.validated_data,
        )
