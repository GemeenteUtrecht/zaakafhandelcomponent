import base64
import logging
from copy import deepcopy
from datetime import date, datetime
from itertools import groupby
from typing import Dict, List

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.http import Http404
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect

from djangorestframework_camel_case.parser import CamelCaseMultiPartParser
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import (
    authentication,
    exceptions,
    permissions,
    serializers,
    status,
    views,
)
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from zds_client.client import ClientError
from zgw_consumers.api_models.constants import (
    RolOmschrijving,
    VertrouwelijkheidsAanduidingen,
)
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.concurrent import parallel
from zgw_consumers.models import Service

from zac.accounts.api.permissions import HasTokenAuth
from zac.accounts.authentication import ApplicationTokenAuthentication
from zac.accounts.models import User, UserAtomicPermission
from zac.camunda.process_instances import get_process_instances
from zac.camunda.processes import start_process
from zac.contrib.brp.api import fetch_extrainfo_np
from zac.contrib.dowc.api import check_document_status
from zac.contrib.objects.services import (
    fetch_start_camunda_process_form_for_zaaktype,
    fetch_zaaktypeattributen_objects_for_zaaktype,
)
from zac.core.camunda.start_process.serializers import CreatedProcessInstanceSerializer
from zac.core.camunda.utils import resolve_assignee
from zac.core.models import MetaObjectTypesConfig
from zac.core.services import (
    fetch_objecttype_version,
    fetch_objecttypes,
    search_objects,
    update_document,
    update_zaak_eigenschap,
)
from zac.elasticsearch.api import update_informatieobject_document
from zac.utils.exceptions import PermissionDeniedSerializer
from zac.utils.filters import ApiFilterBackend
from zgw.models.zrc import Zaak

from ..cache import invalidate_zaak_cache, invalidate_zaakobjecten_cache
from ..services import (
    create_document,
    create_rol,
    create_zaak_eigenschap,
    delete_rol,
    delete_zaak_eigenschap,
    delete_zaakobject,
    fetch_latest_audit_trail_data_document,
    fetch_zaak_eigenschap,
    fetch_zaakobject,
    fetch_zaaktype,
    find_zaak,
    get_catalogi,
    get_document,
    get_eigenschap,
    get_eigenschappen_for_zaaktypen,
    get_informatieobjecttype,
    get_informatieobjecttypen_for_zaak,
    get_related_zaken,
    get_resultaat,
    get_rollen,
    get_roltype,
    get_roltypen,
    get_statussen,
    get_statustype,
    get_statustypen,
    get_zaak,
    get_zaakeigenschappen,
    get_zaakobjecten,
    get_zaaktype,
    get_zaaktypen,
    relate_document_to_zaak,
    zet_status,
)
from ..zaakobjecten import GROUPS, ZaakObjectGroup, noop
from .data import VertrouwelijkheidsAanduidingData
from .filters import (
    EigenschappenFilterSet,
    ObjectTypeFilterSet,
    ZaakEigenschappenFilterSet,
    ZaakObjectFilterSet,
    ZaakRolFilterSet,
    ZaaktypenFilterSet,
)
from .pagination import BffPagination, ProxyPagination
from .permissions import (
    CanAddOrUpdateZaakDocuments,
    CanAddRelations,
    CanAddReverseRelations,
    CanCreateZaken,
    CanForceAddRelations,
    CanForceAddReverseRelations,
    CanForceEditClosedZaak,
    CanForceEditClosedZaken,
    CanHandleAccessRequests,
    CanReadOrUpdateZaken,
    CanReadZaken,
    CanUpdateZaken,
)
from .serializers import (
    AddZaakDocumentSerializer,
    AddZaakRelationSerializer,
    CatalogusSerializer,
    CreateZaakEigenschapSerializer,
    CreateZaakSerializer,
    DeleteZaakRelationSerializer,
    DestroyRolSerializer,
    DocumentInfoSerializer,
    ExpandParamSerializer,
    ExtraInfoSubjectSerializer,
    ExtraInfoUpSerializer,
    FetchZaakDetailUrlSerializer,
    GetZaakDocumentSerializer,
    InformatieObjectTypeSerializer,
    ObjectFilterProxySerializer,
    ObjecttypeProxySerializer,
    ObjecttypeVersionProxySerializer,
    PaginatedObjectProxySerializer,
    ReadRolSerializer,
    RelatedZaakSerializer,
    RolMedewerkerSerializer,
    RolSerializer,
    RolTypeSerializer,
    SearchEigenschapSerializer,
    StatusTypeSerializer,
    UpdateZaakDetailSerializer,
    UpdateZaakDocumentSerializer,
    UpdateZaakEigenschapWaardeSerializer,
    UserAtomicPermissionSerializer,
    VertrouwelijkheidsAanduidingSerializer,
    ZaakDetailSerializer,
    ZaakEigenschapSerializer,
    ZaakHistorySerializer,
    ZaakObjectGroupSerializer,
    ZaakObjectProxySerializer,
    ZaakStatusSerializer,
    ZaakTypeAggregateSerializer,
)
from .utils import convert_eigenschap_spec_to_json_schema

logger = logging.getLogger(__name__)


class GetDocumentInfoView(views.APIView):
    schema = None

    def get(self, request: Request) -> Response:
        document_url = request.query_params.get("document")
        if not document_url:
            raise exceptions.ValidationError(
                _("'document' query parameter is required.")
            )

        document = get_document(document_url)
        document.informatieobjecttype = get_informatieobjecttype(
            document.informatieobjecttype
        )

        serializer = DocumentInfoSerializer(
            instance=document, context={"request": request}
        )
        return Response(serializer.data)


class PostExtraInfoSubjectView(views.APIView):
    schema = None

    @method_decorator(csrf_protect)
    def post(self, request: Request, **kwargs) -> Response:
        # Serialize data from request.query_params
        fields_serializer = ExtraInfoUpSerializer(data=request.data)
        fields_serializer.is_valid(raise_exception=True)

        burgerservicenummer = fields_serializer.data["burgerservicenummer"]
        doelbinding = fields_serializer.data["doelbinding"]
        fields = fields_serializer.data["fields"]

        expand_serializer = ExpandParamSerializer(data={"fields": fields})
        expand_serializer.is_valid(raise_exception=True)
        expand = expand_serializer.data["fields"]

        # Make request_kwargs
        request_kwargs = {
            "headers": {"X-NLX-Request-Subject-Identifier": doelbinding},
            "params": {
                "fields": fields,
                "expand": expand,
            },
        }

        # Set burgerservicenummer in kwargs
        kwargs["burgerservicenummer"] = burgerservicenummer

        # Get extra info
        extra_info_inp = fetch_extrainfo_np(request_kwargs=request_kwargs, **kwargs)
        extra_info_inp.clean_verblijfplaats()

        serializer = ExtraInfoSubjectSerializer(extra_info_inp)
        return Response(serializer.data)


# Backend-For-Frontend endpoints (BFF)


class CreateZaakView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanCreateZaken,
    )
    serializer_class = CreateZaakSerializer

    def get_serializer(self, **kwargs):
        return self.serializer_class(**kwargs)

    @extend_schema(
        summary=_("Let users create a ZAAK."),
        responses={201: CreatedProcessInstanceSerializer},
    )
    def post(self, request):
        """
        Note: If a ZAAK has a ZAAKTYPE that has ROLTYPE with `omschrijving_generiek`: `initiator`
        this will automatically set the requesting user as the initiator.

        """
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        details = start_process(
            process_key=settings.CREATE_ZAAK_PROCESS_DEFINITION_KEY,
            variables=serializer.validated_data,
        )

        return Response(details, status=status.HTTP_201_CREATED)


class GetZaakMixin:
    def get_object(self):
        if not self.kwargs:  # shut up drf-spectular
            return None
        try:
            zaak = find_zaak(**self.kwargs)
        except ObjectDoesNotExist:
            raise Http404("No ZAAK matches the given query.")
        self.check_object_permissions(self.request, zaak)
        return zaak


class ZaakDetailUrlView(GetZaakMixin, views.APIView):
    authentication_classes = (ApplicationTokenAuthentication,)
    permission_classes = (HasTokenAuth,)
    serializer_class = FetchZaakDetailUrlSerializer

    @extend_schema(
        summary=_("Let an application retrieve a direct link to the zaak-detail page."),
        parameters=[
            OpenApiParameter(
                "zaak",
                OpenApiTypes.URI,
                OpenApiParameter.QUERY,
                required=True,
            )
        ],
    )
    def get(self, request, bronorganisatie, identificatie):
        zaak = self.get_object()
        serializer = self.serializer_class(instance=zaak, context={"request": request})
        return Response(serializer.data)


class ZaakDetailView(GetZaakMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadOrUpdateZaken,
        CanForceEditClosedZaken,
    )

    def get_serializer(self, **kwargs):
        mapping = {"GET": ZaakDetailSerializer, "PATCH": UpdateZaakDetailSerializer}
        return mapping[self.request.method](**kwargs)

    def get_camunda_context(self, zaak: Zaak):
        mapping = {
            "camunda_form": [
                fetch_start_camunda_process_form_for_zaaktype,
                zaak.zaaktype,
            ],
            "process_instances": [get_process_instances, zaak.url],
        }
        results = dict()
        with parallel(max_workers=settings.MAX_WORKERS) as executor:
            running_tasks = {
                key: executor.submit(*task) for key, task in mapping.items()
            }
            for key, running_task in running_tasks.items():
                results[key] = running_task.result()
        return results

    @extend_schema(
        summary=_("Retrieve ZAAK."),
        responses={
            200: ZaakDetailSerializer,
            403: PermissionDeniedSerializer,
        },
    )
    def get(
        self, request: Request, bronorganisatie: str, identificatie: str
    ) -> Response:
        zaak = self.get_object()
        zaak.resultaat = get_resultaat(zaak)
        camunda_context = self.get_camunda_context(zaak)
        context = {
            **camunda_context,
            "zaak": zaak,
            "request": request,
        }
        serializer = self.get_serializer(instance=zaak, context=context)
        return Response(serializer.data)

    @extend_schema(
        summary=_("Partially update ZAAK."),
        request=UpdateZaakDetailSerializer,
        responses={
            204: None,
            403: PermissionDeniedSerializer,
        },
    )
    def patch(self, request: Request, bronorganisatie: str, identificatie) -> Response:
        zaak = self.get_object()
        service = Service.get_service(zaak.url)
        client = service.build_client()

        serializer = self.get_serializer(
            data=request.data,
            context={"zaak": self.get_object(), "request": self.request},
        )
        serializer.is_valid(raise_exception=True)

        # If no errors are raised - data is valid too.
        data = deepcopy(serializer.data)
        reden = data.pop("reden", None)
        headers = {"Accept-Crs": "EPSG:4326", "Content-Crs": "EPSG:4326"}
        if reden:
            headers["X-Audit-Toelichting"] = reden
        request_kwargs = {"headers": headers}

        client.partial_update(
            "zaak",
            data,
            url=zaak.url,
            request_kwargs=request_kwargs,
        )
        invalidate_zaak_cache(zaak=zaak)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ZaakStatusesView(GetZaakMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadOrUpdateZaken,
        CanForceEditClosedZaken,
    )
    serializer_class = ZaakStatusSerializer

    @extend_schema(summary=_("List ZAAK STATUSsen."))
    def get(self, request, *args, **kwargs):
        zaak = self.get_object()
        statussen = get_statussen(zaak)
        serializer = self.serializer_class(
            instance=statussen, many=True, context={"zaaktype": zaak.zaaktype}
        )
        return Response(serializer.data)

    @extend_schema(summary=_("Add STATUS to ZAAK."))
    def post(self, request, *args, **kwargs):
        zaak = self.get_object()
        serializer = self.serializer_class(
            data=request.data, context={"zaaktype": zaak.zaaktype}
        )
        serializer.is_valid(raise_exception=True)
        statustype = get_statustype(serializer.validated_data["statustype"]["url"])
        new_status = zet_status(
            zaak,
            statustype,
            toelichting=serializer.validated_data["statustoelichting"],
        )
        serializer = self.serializer_class(
            instance=new_status, context={"zaaktype": zaak.zaaktype}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ZaakEigenschappenView(GetZaakMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadZaken,
    )
    serializer_class = ZaakEigenschapSerializer
    schema_summary = _("List ZAAKEIGENSCHAPpen.")

    def get(self, request, **kwargs):
        zaak = self.get_object()
        serializer = self.serializer_class(
            instance=get_zaakeigenschappen(zaak),
            context={"request": self.request, "view": self},
            many=True,
        )
        return Response(serializer.data)


class ZaakEigenschapDetailView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanUpdateZaken,
        CanForceEditClosedZaken,
    )
    serializer_class = ZaakEigenschapSerializer
    filterset_class = ZaakEigenschappenFilterSet

    def get_object(self):
        filterset = self.filterset_class(
            data=self.request.query_params, request=self.request
        )
        if not filterset.is_valid():
            raise exceptions.ValidationError(filterset.errors)

        url = self.request.query_params.get("url")

        try:
            zaak_eigenschap = fetch_zaak_eigenschap(url)
        except ClientError as exc:
            raise Http404("No ZAAKEIGENSCHAP matches the given url.")

        # check permissions
        zaak = get_zaak(zaak_url=zaak_eigenschap.zaak)
        self.check_object_permissions(self.request, zaak)

        return zaak_eigenschap

    @extend_schema(
        summary=_("Create ZAAKEIGENSCHAP."), request=CreateZaakEigenschapSerializer
    )
    def post(self, request, *args, **kwargs):
        serializer = CreateZaakEigenschapSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get zaak
        zaak = get_zaak(zaak_url=serializer.validated_data["zaak_url"])

        # Create zaakeigenschap
        zaak_eigenschap = create_zaak_eigenschap(
            request=request, **serializer.validated_data
        )
        if not zaak_eigenschap:
            raise exceptions.NotFound(
                detail=_(
                    "EIGENSCHAP with name {eigenschap} not found for zaaktype {zaaktype}."
                ).format(
                    eigenschap=serializer.validated_data["naam"], zaaktype=zaak.zaaktype
                )
            )
        # Resolve relation
        zaak_eigenschap.eigenschap = get_eigenschap(zaak_eigenschap.eigenschap)

        serializer = self.serializer_class(instance=zaak_eigenschap)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary=_("Partially update ZAAKEIGENSCHAP."),
        parameters=[
            OpenApiParameter(
                name="url",
                required=True,
                type=OpenApiTypes.URI,
                description=_("URL-reference of ZAAKEIGENSCHAP in ZAKEN API"),
                location=OpenApiParameter.QUERY,
            )
        ],
        request=UpdateZaakEigenschapWaardeSerializer,
    )
    def patch(self, request, *args, **kwargs):
        zaak_eigenschap = self.get_object()
        serializer = self.serializer_class(
            instance=zaak_eigenschap, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        updated_zaak_eigenschap = update_zaak_eigenschap(
            zaak_eigenschap, request.data, request=request
        )
        # Resolve relation
        updated_zaak_eigenschap.eigenschap = get_eigenschap(
            updated_zaak_eigenschap.eigenschap
        )
        serializer = self.serializer_class(instance=updated_zaak_eigenschap)
        return Response(serializer.data)

    @extend_schema(
        summary=_("Delete ZAAKEIGENSCHAP."),
        parameters=[
            OpenApiParameter(
                name="url",
                required=True,
                type=OpenApiTypes.URI,
                description=_("URL-reference of ZAAKEIGENSCHAP in ZAKEN API"),
                location=OpenApiParameter.QUERY,
            )
        ],
        request=None,
    )
    def delete(self, request, *args, **kwargs):
        zaak_eigenschap = self.get_object()
        delete_zaak_eigenschap(zaak_eigenschap.url)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RelatedZakenView(GetZaakMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadZaken,
    )
    serializer_class = RelatedZaakSerializer
    schema_summary = _("List related ZAAKen.")

    def get(self, request, *args, **kwargs):
        zaak = self.get_object()
        related_zaken = [
            {
                "aard_relatie": aard_relatie,
                "zaak": zaak,
            }
            for aard_relatie, zaak in get_related_zaken(zaak)
        ]

        serializer = self.serializer_class(
            instance=related_zaken, many=True, context={"request": self.request}
        )
        return Response(serializer.data)


class ZaakRelationView(views.APIView):
    permission_classes = (
        permissions.IsAuthenticated,
        CanAddRelations,
        CanAddReverseRelations,
        CanForceAddRelations,
        CanForceAddReverseRelations,
    )

    def get_serializer(self, *args, **kwargs):
        mapping = {
            "POST": AddZaakRelationSerializer,
            "DELETE": DeleteZaakRelationSerializer,
        }
        return mapping[self.request.method](*args, **kwargs)

    def update_in_open_zaak(self, hoofdzaak: Zaak, bijdragezaak: Zaak):
        client = Service.get_client(hoofdzaak.url)
        client.partial_update(
            "zaak",
            {"relevanteAndereZaken": hoofdzaak.relevante_andere_zaken},
            url=hoofdzaak.url,
        )
        client.partial_update(
            "zaak",
            {"relevanteAndereZaken": bijdragezaak.relevante_andere_zaken},
            url=bijdragezaak.url,
        )
        # Invalidate cache immediately
        invalidate_zaak_cache(hoofdzaak)
        invalidate_zaak_cache(bijdragezaak)

    def perform_create(self, serializer):
        # Retrieving the main and bijdrage zaak
        hoofdzaak_url = serializer.validated_data["hoofdzaak"]
        bijdragezaak_url = serializer.validated_data["bijdragezaak"]
        hoofdzaak = get_zaak(zaak_url=hoofdzaak_url)
        bijdragezaak = get_zaak(zaak_url=bijdragezaak_url)
        # Add the relation (from to main to related)
        hoofdzaak.relevante_andere_zaken.append(
            {
                "url": bijdragezaak_url,
                "aardRelatie": serializer.validated_data["aard_relatie"],
            }
        )
        # Add the reverse relation
        bijdragezaak.relevante_andere_zaken.append(
            {
                "url": hoofdzaak_url,
                "aardRelatie": serializer.validated_data[
                    "aard_relatie_omgekeerde_richting"
                ],
            }
        )
        self.update_in_open_zaak(hoofdzaak, bijdragezaak)
        return serializer

    @extend_schema(
        summary=_("Add related ZAAK."),
        description=_("Relate a ZAAK to another ZAAK and create the reverse relation."),
    )
    def post(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer = self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, serializer):
        # Retrieving the main and bijdrage zaak
        hoofdzaak_url = serializer.validated_data["hoofdzaak"]
        bijdragezaak_url = serializer.validated_data["bijdragezaak"]
        hoofdzaak = get_zaak(zaak_url=hoofdzaak_url)
        bijdragezaak = get_zaak(zaak_url=bijdragezaak_url)

        # Delete the relation (from to main to related)
        hoofdzaak.relevante_andere_zaken = [
            zaakrelatie
            for zaakrelatie in hoofdzaak.relevante_andere_zaken
            if zaakrelatie["url"] != bijdragezaak_url
        ]
        # Delete the relation (from to related to main)
        bijdragezaak.relevante_andere_zaken = [
            zaakrelatie
            for zaakrelatie in bijdragezaak.relevante_andere_zaken
            if zaakrelatie["url"] != hoofdzaak_url
        ]
        self.update_in_open_zaak(hoofdzaak, bijdragezaak)
        return serializer

    @extend_schema(
        summary=_("Delete ZAAK relation."),
        description=_(
            "Delete the relationship of a ZAAK to another ZAAK and possible the reverse relation as well."
        ),
    )
    def delete(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_destroy(serializer)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ZaakRolesView(GetZaakMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadOrUpdateZaken,
        CanForceEditClosedZaken,
    )
    filterset_class = ZaakRolFilterSet

    def get_serializer(self, **kwargs):
        mapping = {
            "GET": ReadRolSerializer,
            "POST": RolSerializer,
            "DELETE": DestroyRolSerializer,
        }
        return mapping[self.request.method](**kwargs)

    @extend_schema(
        summary=_("List ROLlen of ZAAK."),
        request=ReadRolSerializer,
        responses={200: ReadRolSerializer},
    )
    def get(self, request, *args, **kwargs):
        zaak = self.get_object()
        rollen = get_rollen(zaak)
        serializer = self.get_serializer(instance=rollen, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary=_("Add ROL to ZAAK."),
        request=RolSerializer,
        responses={201: RolSerializer},
    )
    def post(self, request, *args, **kwargs):
        zaak = self.get_object()
        data = {**request.data, "zaak": zaak.url}
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        # For the reasons below we check if the rol to be created is a hoofdbehandelaar:
        #
        # Open zaak does not support changing roles or assigning a hoofdbehandelaar.
        # We use the `behandelaar` roltype to set our `hoofdbehandelaar`, but we typically only want one
        # and at the same time we don't want a ZAAK to not have a (hoofd)behandelaar.
        #
        # If it is a hoofdbehandelaar rol we first delete the old hoofdbehandelaar rol.

        roltype = get_roltype(serializer.data["roltype"])
        if roltype.omschrijving == "Hoofdbehandelaar":
            rollen = get_rollen(zaak)
            rol_url = [
                rol.url for rol in rollen if rol.omschrijving == "Hoofdbehandelaar"
            ]
            if rol_url:
                delete_rol(rol_url[0], zaak, user=request.user)
        try:
            rol = create_rol(serializer.data)
        except Exception as exc:
            if exc.args[0].get("status") == 400:
                raise serializers.ValidationError(
                    exc.args[0].get("invalidParams", "Something went wrong.")
                )
            raise exc

        serializer = self.get_serializer(instance=rol)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary=_("Destroy ROL from ZAAK."),
        description=_(
            "This also adds an `oudbehandelaar` to the `oudbehandelaren` object of the ZAAK if the ROL has `omschrijving_generiek`: `{behandelaar}`, and it invalidates the cache of the `oudbehandelaren` object."
        ).format(behandelaar=RolOmschrijving.behandelaar),
        parameters=[
            OpenApiParameter(
                name="url",
                required=True,
                type=OpenApiTypes.URI,
                description=_("URL-reference of ROL in ZAKEN API"),
                location=OpenApiParameter.QUERY,
            )
        ],
        request=DestroyRolSerializer,
        responses={204: None},
    )
    def delete(self, request, *args, **kwargs):
        filterset = self.filterset_class(
            data=self.request.query_params, request=self.request
        )
        if not filterset.is_valid():
            raise exceptions.ValidationError(filterset.errors)

        zaak = self.get_object()
        serializer = self.get_serializer(
            data=self.request.query_params, context={"zaak": zaak}
        )
        serializer.is_valid(raise_exception=True)
        delete_rol(serializer.validated_data["url"], zaak, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RolBetrokkeneIdentificatieView(GetZaakMixin, views.APIView):
    authentication_classes = (ApplicationTokenAuthentication,)
    permission_classes = (HasTokenAuth,)
    serializer_class = RolMedewerkerSerializer

    @extend_schema(
        summary=_("Retrieve `betrokkene_identificatie` of ZAC `medewerker`."),
        tags=["meta"],
        request=RolMedewerkerSerializer,
        responses={200: RolMedewerkerSerializer},
    )
    def post(self, request):
        user = resolve_assignee(
            request.data["betrokkene_identificatie"]["identificatie"]
        )
        serializer = self.serializer_class(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


class ZaakObjectsView(GetZaakMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadZaken,
    )
    serializer_class = ZaakObjectGroupSerializer
    schema_summary = _("List related OBJECTs of a ZAAK.")

    def get(self, request, *args, **kwargs):
        """
        Note: These objects do not include objects related to `meta` objecttypes.

        """
        zaak = self.get_object()
        zaakobjecten = get_zaakobjecten(zaak)

        def group_key(zo):
            if zo.object_type == "overige":
                return zo.object_type_overige
            return zo.object_type

        # re-group by type
        groups = []
        zaakobjecten = sorted(zaakobjecten, key=group_key)
        grouped = groupby(zaakobjecten, key=group_key)
        for _group, items in grouped:
            group = GROUPS.get(
                _group,
                ZaakObjectGroup(object_type=_group, label=_group, retriever=noop),
            )
            group.retrieve_items(items)
            if group.items:
                groups.append(group)

        serializer = self.serializer_class(instance=groups, many=True)
        return Response(serializer.data)


@extend_schema(summary=_("List ZAAK users and atomic permissions."))
class ZaakAtomicPermissionsView(GetZaakMixin, ListAPIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanHandleAccessRequests,
    )
    queryset = User.objects.all()

    def get_serializer_class(self):
        return UserAtomicPermissionSerializer

    def filter_queryset(self, queryset):
        zaak = self.get_object()
        return (
            queryset.filter(atomic_permissions__object_url=zaak.url)
            .prefetch_related(
                models.Prefetch(
                    "useratomicpermission_set",
                    queryset=UserAtomicPermission.objects.select_related(
                        "atomic_permission"
                    )
                    .filter(atomic_permission__object_url=zaak.url)
                    .actual(),
                    to_attr="zaak_atomic_permissions",
                )
            )
            .distinct()
        )


###############################
#          Documents          #
###############################


class ZaakDocumentView(views.APIView):
    permission_classes = (
        permissions.IsAuthenticated,
        CanAddOrUpdateZaakDocuments,
        CanUpdateZaken,
        CanForceEditClosedZaak,
    )
    parser_classes = (CamelCaseMultiPartParser,)

    def get_serializer(self, *args, **kwargs):
        if self.request.method == "PATCH":
            return UpdateZaakDocumentSerializer(*args, **kwargs)
        return AddZaakDocumentSerializer(*args, **kwargs)

    def get_document_data(self, validated_data: dict, zaak: Zaak) -> Dict[str, str]:
        document_data = {
            "bronorganisatie": zaak.bronorganisatie,  # TODO: what if it's different?
            "creatiedatum": date.today().isoformat(),  # TODO: what if it's created on another date
            "auteur": self.request.user.get_full_name() or self.request.user.username,
            "taal": "nld",
            "ontvangstdatum": date.today().isoformat(),
        }

        uploaded_file = validated_data.pop("file", None)
        if uploaded_file:
            with uploaded_file.open("rb") as content:
                inhoud = base64.b64encode(content.read())

            document_data.update(
                {
                    "bestandsnaam": uploaded_file.name,
                    "formaat": uploaded_file.content_type,
                    "inhoud": inhoud.decode(
                        "ascii"
                    ),  # it's base64, so ascii compatible
                    "titel": uploaded_file.name,
                    "bestandsomvang": uploaded_file.size,
                }
            )

        return {**document_data, **validated_data}

    def get_document_audit_trail(self, document: Document) -> Dict[str, datetime]:
        latest_audittrail = fetch_latest_audit_trail_data_document(document.url)
        editing_history = {
            latest_audittrail.resource_url: latest_audittrail.last_edited_date
        }
        return editing_history

    def get_response_serializer(self, instance: Document) -> GetZaakDocumentSerializer:
        open_documenten = check_document_status(documents=[instance.url])
        editing_history = self.get_document_audit_trail(instance)
        serializer = GetZaakDocumentSerializer(
            instance=instance,
            context={
                "open_documenten": {dowc.document: dowc for dowc in open_documenten},
                "editing_history": editing_history,
                "request": self.request,
            },
        )
        return serializer

    @extend_schema(
        summary=_("Partially update ZAAK document."),
        responses=GetZaakDocumentSerializer,
    )
    def patch(self, request: Request, *args, **kwargs) -> Response:
        """
        Patch an already uploaded document on the Documenten API.
        """
        serializer = self.get_serializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        audit_line = serializer.validated_data.pop("reden")
        document_url = serializer.validated_data.pop("url")
        document = get_document(document_url)

        zaak = get_zaak(zaak_url=serializer.validated_data["zaak"])
        document_data = self.get_document_data(serializer.validated_data, zaak)
        document = update_document(document_url, document_data, audit_line)

        document.informatieobjecttype = get_informatieobjecttype(
            document.informatieobjecttype
        )

        # update elasticsearch index
        update_informatieobject_document(document)

        serializer = self.get_response_serializer(document)
        return Response(serializer.data)

    @extend_schema(
        summary=_("Add document to ZAAK."),
        responses=GetZaakDocumentSerializer,
    )
    def post(self, request: Request, *args, **kwargs) -> Response:
        """
        Upload a document to the Documenten API and relate it to a ZAAK.
        """
        serializer = self.get_serializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        zaak = get_zaak(zaak_url=serializer.validated_data["zaak"])
        url = serializer.validated_data.get("url")

        if url:
            # Document already exists, don't need to create it
            document = get_document(url)

        else:
            # create document in Documenten API
            document_data = self.get_document_data(serializer.validated_data, zaak)
            document = create_document(document_data)

        relate_document_to_zaak(document.url, zaak.url)
        document.informatieobjecttype = get_informatieobjecttype(
            document.informatieobjecttype
        )

        # add to elasticsearch index
        update_informatieobject_document(document)

        serializer = self.get_response_serializer(document)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


###############################
#  META / Catalogi API views  #
###############################


@extend_schema(
    summary=_("List INFORMATIEOBJECTTYPEs for a ZAAK."),
    tags=["meta"],
    parameters=[
        OpenApiParameter(
            name="zaak",
            required=True,
            type=OpenApiTypes.URI,
            description=_("ZAAK to list available INFORMATIEOBJECTTYPEs for."),
            location=OpenApiParameter.QUERY,
        )
    ],
)
class InformatieObjectTypeListView(views.APIView):
    """
    List the available document types for a given zaak.

    """

    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = InformatieObjectTypeSerializer
    filter_backends = ()

    def get(self, request, *args, **kwargs):
        zaak_url = self.request.query_params.get("zaak")
        if not zaak_url:
            raise exceptions.ValidationError("'zaak' query parameter is required.")
        iots = get_informatieobjecttypen_for_zaak(zaak_url)
        iots = [iot for iot in iots if iot.omschrijving not in settings.FILTERED_IOTS]
        return Response(self.serializer_class(iots, many=True).data)


@extend_schema(summary=_("List CATALOGI."), tags=["meta"])
class CatalogiView(views.APIView):
    """
    List a collection of catalogi.

    """

    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CatalogusSerializer

    def get(self, request, *args, **kwargs):
        return Response(self.serializer_class(get_catalogi(), many=True).data)


@extend_schema(summary=_("List ZAAKTYPEs."), tags=["meta"])
class ZaakTypenView(ListAPIView):
    """
    List a collection of zaaktypen available to the end user.

    Different versions of the same zaaktype are aggregated. Only the zaaktypen that
    the authenticated user has read-permissions for are returned.
    """

    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ZaakTypeAggregateSerializer
    pagination_class = BffPagination
    filter_backends = (ApiFilterBackend,)
    filterset_class = ZaaktypenFilterSet
    action = "list"

    def get_queryset(self) -> List[dict]:
        zaaktypen = self.get_zaaktypen()
        return zaaktypen

    def get_zaaktypen(self) -> List[dict]:
        zaaktypen = sorted(
            get_zaaktypen(self.request), key=lambda zt: zt.versiedatum, reverse=True
        )

        # aggregate
        zaaktypen_aggregated = []
        for zt in zaaktypen:
            omschrijving_found = zt.omschrijving in [
                _zt.omschrijving for _zt in zaaktypen_aggregated
            ]
            catalogus_found = zt.catalogus in [
                _zt.catalogus
                for _zt in zaaktypen_aggregated
                if _zt.omschrijving == zt.omschrijving
            ]

            if not omschrijving_found or (omschrijving_found and not catalogus_found):
                zaaktypen_aggregated.append(zt)

        # resolve catalogus
        catalogi = {cat.url: cat for cat in get_catalogi()}
        for zt in zaaktypen_aggregated:
            zt.catalogus = catalogi[zt.catalogus]

        zaaktypen_aggregated = sorted(
            sorted(zaaktypen_aggregated, key=lambda zt: zt.catalogus.domein),
            key=lambda zt: zt.omschrijving,
        )
        return zaaktypen_aggregated


@extend_schema(summary=_("List vertrouwelijkheidaanduidingen."), tags=["meta"])
class VertrouwelijkheidsAanduidingenView(views.APIView):
    """
    List the available vertrouwelijkheidaanduidingen.
    """

    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = VertrouwelijkheidsAanduidingSerializer

    def get(self, request, **kwargs):
        serializer = self.serializer_class(
            instance=[
                VertrouwelijkheidsAanduidingData(label=choice[1], value=choice[0])
                for choice in VertrouwelijkheidsAanduidingen.choices
            ],
            many=True,
        )
        return Response(serializer.data)


@extend_schema(
    summary=_("List STATUSTYPEs for a ZAAK."),
    tags=["meta"],
    parameters=[
        OpenApiParameter(
            name="zaak",
            required=True,
            type=OpenApiTypes.URI,
            description=_("ZAAK to list available STATUSTYPEs for."),
            location=OpenApiParameter.QUERY,
        )
    ],
)
class StatusTypenView(views.APIView):
    """
    List the available statustypen for the zaak.

    """

    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = StatusTypeSerializer

    def get(self, request):
        zaak_url = request.query_params.get("zaak")
        if not zaak_url:
            raise exceptions.ValidationError(_("'zaak' query parameter is required."))
        zaak = get_zaak(zaak_url=zaak_url)
        zaaktype = fetch_zaaktype(zaak.zaaktype)
        statusstypen = get_statustypen(zaaktype)
        serializer = self.serializer_class(statusstypen, many=True)
        return Response(serializer.data)


@extend_schema(summary=_("List ZAAKTYPE EIGENSCHAPpen."), tags=["meta"])
class EigenschappenView(ListAPIView):
    """
    List the available eigenschappen sorted by name for a given `zaaktype` OR a `zaaktype_omschrijving` within a `catalogus`.
    If the `zaaktype_omschrijving` is submitted, the `catalogus` is also required.
    If the `catalogus` is submitted, the `zaaktype_omschrijving` is required.
    The `zaaktype` is mutually exclusive from the `zaaktype_omschrijving` and `catalogus`.

    Given the `zaaktype_omschrijving`, all versions of the matching zaaktype are considered,
    and returns the eigenschappen available for the aggregated set of zaaktype versions.
    Note that only the zaaktypen that the authenticated user has read-permissions for
    are considered.

    The choices for the EIGENSCHAP waarde are retrieved from the objects API if available.

    """

    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = SearchEigenschapSerializer
    filter_backends = (ApiFilterBackend,)
    filterset_class = EigenschappenFilterSet

    def list(self, request, *args, **kwargs):
        # validate query params
        filterset = self.filterset_class(data=request.query_params, request=request)
        if not filterset.is_valid():
            raise exceptions.ValidationError(filterset.errors)

        if zt := request.query_params.get("zaaktype"):
            zaaktype = get_zaaktype(
                zt,
                request=request,
            )
            zaaktypen = [zaaktype] if zaaktype else []

        else:
            zaaktypen = get_zaaktypen(
                request=request,
                catalogus=request.query_params.get("catalogus"),
                identificatie=request.query_params.get("zaaktype_identificatie"),
            )

        if not zaaktypen:
            return Response([])

        zaak_attributes = {
            zatr["naam"]: zatr
            for zatr in fetch_zaaktypeattributen_objects_for_zaaktype(
                zaaktype=zaaktypen[0]
            )
        }
        eigenschappen = get_eigenschappen_for_zaaktypen(zaaktypen)

        for ei in eigenschappen:
            if (zatr := zaak_attributes.get(ei.naam)) and (enum := zatr.get("enum")):
                ei.specificatie.waardenverzameling = enum

        eigenschappen_data = [
            {
                "name": e.naam,
                "spec": convert_eigenschap_spec_to_json_schema(e.specificatie),
            }
            for e in eigenschappen
        ]

        eigenschappen_data = sorted(eigenschappen_data, key=lambda ei: ei["name"])
        serializer = self.get_serializer(eigenschappen_data, many=True)
        return Response(serializer.data)


@extend_schema(
    summary=_("List ROLTYPEs for a ZAAK."),
    tags=["meta"],
    parameters=[
        OpenApiParameter(
            name="zaak",
            required=True,
            type=OpenApiTypes.URI,
            description=_("ZAAK to list available ROLTYPEs for."),
            location=OpenApiParameter.QUERY,
        )
    ],
)
class RolTypenView(views.APIView):
    """
    List the available ROLTYPEs for the zaak.

    """

    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = RolTypeSerializer

    def get(self, request):
        zaak_url = request.query_params.get("zaak")
        if not zaak_url:
            raise exceptions.ValidationError(_("'zaak' query parameter is required."))
        zaak = get_zaak(zaak_url=zaak_url)
        zaaktype = fetch_zaaktype(zaak.zaaktype)
        roltypen = get_roltypen(zaaktype)
        serializer = self.serializer_class(roltypen, many=True)
        return Response(serializer.data)


###############################
#           Objects           #
###############################


class ObjecttypeListView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ObjecttypeProxySerializer
    filterset_class = ObjectTypeFilterSet

    @extend_schema(
        summary=_("List OBJECTTYPEs."),
        description=_(
            "Retrieves all non-meta OBJECTTYPEs from the configured OBJECTTYPES API."
        ),
        tags=["objects"],
        parameters=[
            OpenApiParameter(
                name="zaaktype",
                required=False,
                type=OpenApiTypes.URI,
                description=_("URL-reference of ZAAKTYPE in CATALOGI API."),
                location=OpenApiParameter.QUERY,
            )
        ],
    )
    def get(self, request, *args, **kwargs):
        filterset = self.filterset_class(
            data=self.request.query_params, request=request
        )
        if not filterset.is_valid():
            raise exceptions.ValidationError(filterset.errors)

        meta_ot_urls = list(
            MetaObjectTypesConfig.get_solo().meta_objecttype_urls.values()
        )

        objecttypes = [
            ot for ot in fetch_objecttypes() if ot["url"] not in meta_ot_urls
        ]

        if zt_url := filterset.data.get("zaaktype"):
            zaaktype = fetch_zaaktype(zt_url)
            objecttypes = [
                ot
                for ot in objecttypes
                if zaaktype.identificatie
                in ot.get("labels", {}).get("zaaktypeIdentificaties", [])
            ]
        serializer = self.serializer_class(objecttypes, many=True)
        return Response(serializer.data)


@extend_schema(
    summary=_("Read OBJECTTYPE version."),
    description=_("Read the details of a particular OBJECTTYPE version."),
    tags=["objects"],
)
class ObjecttypeVersionReadView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ObjecttypeVersionProxySerializer

    def get_object(self) -> dict:
        return fetch_objecttype_version(**self.kwargs)

    def get(self, request, *args, **kwargs):
        object = self.get_object()
        serializer = self.serializer_class(
            instance=object, context={"request": self.request, "view": self}
        )
        return Response(serializer.data)


@extend_schema(
    summary=_("Search OBJECTs."),
    description=_("Search for OBJECTs in the OBJECTS API."),
    responses={(200, "application/json"): PaginatedObjectProxySerializer},
    tags=["objects"],
    parameters=[
        OpenApiParameter(
            name=ProxyPagination().page_size_query_param,
            default=ProxyPagination().page_size,
            type=OpenApiTypes.INT,
            description=_("Number of results to return per paginated response."),
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name=ProxyPagination().page_query_param,
            type=OpenApiTypes.INT,
            description=_("Page number of paginated response."),
            location=OpenApiParameter.QUERY,
        ),
    ],
)
class ObjectSearchView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ObjectFilterProxySerializer
    pagination_class = ProxyPagination

    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.
        """
        if not hasattr(self, "_paginator"):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def get_paginated_response(self, data):
        assert self.pagination_class is not None
        serializer = PaginatedObjectProxySerializer(instance=data)
        return self.paginator.get_paginated_response(self.request, serializer.data)

    def post(self, request):
        """
        EXCLUDES `meta`=True objects and hides `meta` field on others.

        """
        pc = self.pagination_class()
        qp = {pc.page_size_query_param: pc.get_page_size(request)}
        if page := request.query_params.get(pc.page_query_param):
            qp[pc.page_query_param] = page

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            objects, _qp = search_objects(
                filters=request.data,
                query_params=qp,
            )
        except ClientError as exc:
            raise ValidationError(detail=exc.args[0])

        return self.get_paginated_response(objects)


class ZaakObjectChangeView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanUpdateZaken,
        CanForceEditClosedZaken,
    )
    serializer_class = ZaakObjectProxySerializer
    filterset_class = ZaakObjectFilterSet

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    @extend_schema(
        summary=_("Create ZAAKOBJECT."),
        description=_(
            "Relate an OBJECT to a ZAAK. OBJECT-ZAAK relation has to be unique or a HTTP 400 error will be raised."
        ),
        responses={(201, "application/json"): ZaakObjectProxySerializer},
        tags=["objects"],
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # check permissions
        zaak_url = serializer.validated_data["zaak"]
        zaak = get_zaak(zaak_url=zaak_url)
        self.check_object_permissions(self.request, zaak)

        created_zaakobject = serializer.save()
        invalidate_zaakobjecten_cache(zaak)
        return Response(status=201, data=created_zaakobject)

    @extend_schema(
        summary=_("Delete ZAAKOBJECT."),
        parameters=[
            OpenApiParameter(
                name="url",
                required=True,
                type=OpenApiTypes.URI,
                description=_("URL-reference of ZAAKOBJECT in ZAKEN API."),
                location=OpenApiParameter.QUERY,
            )
        ],
        tags=["objects"],
    )
    def delete(self, request, *args, **kwargs):
        filterset = self.filterset_class(
            data=self.request.query_params, request=self.request
        )
        if not filterset.is_valid():
            raise exceptions.ValidationError(filterset.errors)
        url = self.request.query_params.get("url")

        try:
            zaak_object = fetch_zaakobject(url)
        except ClientError as exc:
            raise Http404("No ZAAKOBJECT matches the given url.")

        # check permissions
        zaak = get_zaak(zaak_url=zaak_object.zaak)
        self.check_object_permissions(self.request, zaak)

        delete_zaakobject(zaak_object.url)
        invalidate_zaakobjecten_cache(zaak)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecentlyViewedZakenView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadZaken,
    )
    serializer_class = ZaakHistorySerializer

    def get(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            instance=request.user, context={"request": request}
        )
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            instance=request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)