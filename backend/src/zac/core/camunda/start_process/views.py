from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from zac.camunda.api.utils import delete_zaak_creation_process, start_process
from zac.core.api.views import GetZaakMixin
from zac.objects.services import fetch_start_camunda_process_form

from .permissions import CanStartCamundaProcess
from .serializers import CreatedProcessInstanceSerializer


class StartCamundaProcessView(GetZaakMixin, APIView):
    permission_classes = (permissions.IsAuthenticated, CanStartCamundaProcess)

    def get_serializer(self, *args, **kwargs):
        return CreatedProcessInstanceSerializer(*args, **kwargs)

    @extend_schema(summary=_("Start camunda process for ZAAK."))
    def post(
        self, request: Request, bronorganisatie: str, identificatie: str
    ) -> Response:
        zaak = self.get_object()

        # First check to see if there is a zaak creation
        # process still running and delete it if so.
        delete_zaak_creation_process(zaak)

        # See if there is a configured camunda_start_process object
        camunda_start_process = fetch_start_camunda_process_form(zaak.zaaktype)
        results = start_process(
            process_key=camunda_start_process.camunda_process_definition_key,
            variables={
                "zaakUrl": zaak.url,
                "zaakIdentificatie": zaak.identificatie,
                "zaakDetails": {
                    "omschrijving": zaak.omschrijving,
                    "zaaktypeOmschrijving": zaak.zaaktype.omschrijving,
                },
            },
        )
        serializer = self.get_serializer(results)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
