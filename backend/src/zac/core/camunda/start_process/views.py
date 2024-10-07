import logging

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView
from zgw_consumers.api_models.constants import RolOmschrijving

from zac.accounts.api.permissions import HasTokenAuth
from zac.accounts.authentication import ApplicationTokenAuthentication
from zac.camunda.api.utils import get_bptl_app_id_variable
from zac.camunda.constants import AssigneeTypeChoices
from zac.camunda.process_instances import get_process_instances
from zac.camunda.processes import start_process
from zac.contrib.objects.services import fetch_start_camunda_process_form_for_zaaktype
from zac.core.api.permissions import CanForceEditClosedZaak
from zac.core.api.views import GetZaakMixin
from zac.core.camunda.start_process.data import StartCamundaProcessForm
from zac.core.services import get_rollen
from zgw.models import Zaak

from .permissions import CanStartCamundaProcess
from .serializers import CreatedProcessInstanceSerializer

logger = logging.getLogger(__name__)


class StartCamundaProcessView(GetZaakMixin, APIView):
    authentication_classes = [
        ApplicationTokenAuthentication
    ] + api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permission_classes = (
        HasTokenAuth
        | (
            permissions.IsAuthenticated
            & CanStartCamundaProcess
            & CanForceEditClosedZaak
        ),
    )
    serializer_class = CreatedProcessInstanceSerializer

    def get_camunda_form(self, zaak: Zaak) -> StartCamundaProcessForm:
        # See if there is a configured camunda_start_process object
        form = fetch_start_camunda_process_form_for_zaaktype(zaak.zaaktype)
        if not form:
            raise exceptions.NotFound(
                "No start camunda process form found for zaaktype with `identificatie`: `%s`."
                % zaak.zaaktype.identificatie
            )
        return form

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    @extend_schema(summary=_("Start camunda process for ZAAK."))
    def post(
        self, request: Request, bronorganisatie: str, identificatie: str
    ) -> Response:
        zaak = self.get_object()
        form = self.get_camunda_form(zaak)

        # check if old process instance is still running. could be the case if a zaak was terminated earlier
        if zaak.einddatum and (
            process_instances := get_process_instances(
                zaak_url=zaak.url,
                process_definition_key=form.camunda_process_definition_key,
            )
        ):
            process_instances = list(process_instances.values())
            if len(process_instances) > 1:
                logger.warning(
                    "Found more than 1 process instance with parent process definition key for zaak url %s."
                    % zaak.url
                )

            results = {
                "instance_id": process_instances[0].id,
                "instance_url": process_instances[0].get_url(),
            }
        else:
            variables = {
                **get_bptl_app_id_variable(),
                "zaakUrl": zaak.url,
                "zaakIdentificatie": zaak.identificatie,
                "zaakDetails": {
                    "omschrijving": zaak.omschrijving,
                    "zaaktypeOmschrijving": zaak.zaaktype.omschrijving,
                },
            }

            initiator = [
                rol
                for rol in get_rollen(zaak)
                if rol.omschrijving_generiek == RolOmschrijving.initiator
            ]
            if initiator:
                variables["initiator"] = initiator[0].betrokkene_identificatie[
                    "identificatie"
                ]
            elif request.user:
                variables["initiator"] = f"{AssigneeTypeChoices.user}:{request.user}"

            results = start_process(
                process_key=form.camunda_process_definition_key
                if not zaak.einddatum
                else settings.RESTART_ZAAK_PROCESS_DEFINITION_KEY,
                variables=variables,
            )

        serializer = self.get_serializer(results)
        return Response(serializer.data, status=status.HTTP_200_OK)
