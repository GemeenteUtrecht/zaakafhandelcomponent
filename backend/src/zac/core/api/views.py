import base64
import logging
from datetime import date
from itertools import groupby
from typing import Dict, List

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
    generics,
    permissions,
    status,
    views,
)
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from zds_client.client import ClientError
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.concurrent import parallel
from zgw_consumers.models import Service

from zac.accounts.models import User, UserAtomicPermission
from zac.contrib.brp.api import fetch_extrainfo_np
from zac.contrib.dowc.api import get_open_documenten
from zac.core.services import (
    fetch_objecttype_version,
    fetch_objecttypes,
    relate_object_to_zaak,
    search_objects,
    update_document,
    update_zaak_eigenschap,
)
from zac.utils.exceptions import PermissionDeniedSerializer
from zac.utils.filters import ApiFilterBackend
from zgw.models.zrc import Zaak

from ..cache import invalidate_zaak_cache
from ..services import (
    create_document,
    delete_zaak_eigenschap,
    delete_zaak_object,
    fetch_zaak_eigenschap,
    fetch_zaak_object,
    fetch_zaaktype,
    find_zaak,
    get_document,
    get_documenten,
    get_eigenschappen,
    get_informatieobjecttype,
    get_related_zaken,
    get_resultaat,
    get_rollen,
    get_statussen,
    get_statustype,
    get_statustypen,
    get_zaak,
    get_zaak_eigenschappen,
    get_zaakobjecten,
    get_zaaktypen,
    relate_document_to_zaak,
    resolve_documenten_informatieobjecttypen,
    zet_status,
)
from ..views.utils import filter_documenten_for_permissions
from ..zaakobjecten import GROUPS, ZaakObjectGroup, noop
from .data import VertrouwelijkheidsAanduidingData
from .filters import (
    EigenschappenFilterSet,
    ZaakEigenschappenFilterSet,
    ZaakObjectFilterSet,
    ZaaktypenFilterSet,
)
from .mixins import ListMixin, RetrieveMixin
from .pagination import BffPagination
from .permissions import (
    CanAddOrUpdateZaakDocuments,
    CanAddRelations,
    CanHandleAccessRequests,
    CanReadOrUpdateZaken,
    CanReadZaken,
    CanUpdateZaken,
)
from .serializers import (
    AddZaakDocumentSerializer,
    AddZaakRelationSerializer,
    DocumentInfoSerializer,
    ExpandParamSerializer,
    ExtraInfoSubjectSerializer,
    ExtraInfoUpSerializer,
    GetZaakDocumentSerializer,
    InformatieObjectTypeSerializer,
    ObjectFilterProxySerializer,
    ObjectProxySerializer,
    ObjecttypeProxySerializer,
    ObjecttypeVersionProxySerializer,
    RelatedZaakSerializer,
    RolSerializer,
    SearchEigenschapSerializer,
    StatusTypeSerializer,
    UpdateZaakDetailSerializer,
    UpdateZaakDocumentSerializer,
    UserAtomicPermissionSerializer,
    VertrouwelijkheidsAanduidingSerializer,
    ZaakDetailSerializer,
    ZaakEigenschapSerializer,
    ZaakObjectGroupSerializer,
    ZaakObjectProxySerializer,
    ZaakStatusSerializer,
    ZaakTypeAggregateSerializer,
)
from .utils import (
    convert_eigenschap_spec_to_json_schema,
    get_informatieobjecttypen_for_zaak,
)

logger = logging.getLogger(__name__)


class GetDocumentInfoView(views.APIView):
    schema = None

    def get(self, request: Request) -> Response:
        document_url = request.query_params.get("document")
        if not document_url:
            raise exceptions.ValidationError("'document' query parameter is required.")

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


class GetZaakMixin:
    def get_object(self):
        try:
            zaak = find_zaak(**self.kwargs)
        except ObjectDoesNotExist:
            raise Http404("No zaak matches the given query.")
        self.check_object_permissions(self.request, zaak)
        return zaak


class ZaakDetailView(GetZaakMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanReadOrUpdateZaken,)

    def get_serializer(self, **kwargs):
        mapping = {"GET": ZaakDetailSerializer, "PATCH": UpdateZaakDetailSerializer}
        return mapping[self.request.method](**kwargs)

    @extend_schema(
        summary=_("Retrieve case details"),
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
        serializer = self.get_serializer(instance=zaak)
        return Response(serializer.data)

    @extend_schema(
        summary=_("Update case details"),
        responses={
            204: None,
            403: PermissionDeniedSerializer,
        },
    )
    def patch(self, request: Request, bronorganisatie: str, identificatie) -> Response:
        zaak = self.get_object()
        service = Service.get_service(zaak.url)
        client = service.build_client()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # If no errors are raised - data is valid too.
        data = {**serializer.data}
        reden = data.pop("reden")

        client.partial_update(
            "zaak",
            data,
            url=zaak.url,
            request_kwargs={"headers": {"X-Audit-Toelichting": reden}},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ZaakStatusesView(GetZaakMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanReadOrUpdateZaken,)
    serializer_class = ZaakStatusSerializer

    @extend_schema(summary=_("List case statussen"))
    def get(self, request, *args, **kwargs):
        zaak = self.get_object()
        statussen = get_statussen(zaak)
        serializer = self.serializer_class(instance=statussen, many=True)
        return Response(serializer.data)

    @extend_schema(summary=_("Add case status"))
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
        serializer = self.serializer_class(instance=new_status)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ZaakEigenschappenView(GetZaakMixin, ListMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanReadZaken,)
    serializer_class = ZaakEigenschapSerializer
    schema_summary = _("List case properties (eigenschappen)")

    def get_objects(self):
        zaak = self.get_object()
        return get_zaak_eigenschappen(zaak)


class ZaakEigenschapDetailView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanUpdateZaken,)
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
            raise Http404("No zaak eigenschap matches the given url.")

        # check permissions
        zaak = get_zaak(zaak_url=zaak_eigenschap.zaak)
        self.check_object_permissions(self.request, zaak)

        return zaak_eigenschap

    @extend_schema(
        summary=_("Update case property"),
        parameters=[
            OpenApiParameter(
                name="url",
                required=True,
                type=OpenApiTypes.URI,
                description=_("URL reference of ZAAK EIGENSCHAP in ZAKEN API"),
                location=OpenApiParameter.QUERY,
            )
        ],
    )
    def patch(self, request, *args, **kwargs):
        zaak_eigenschap = self.get_object()

        serializer = self.serializer_class(
            instance=zaak_eigenschap, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        data = {"waarde": str(serializer.initial_data["value"])}

        updated_zaak_eigenschap = update_zaak_eigenschap(zaak_eigenschap.url, data)
        serializer = self.serializer_class(instance=updated_zaak_eigenschap)
        return Response(serializer.data)

    @extend_schema(
        summary=_("Delete case property"),
        parameters=[
            OpenApiParameter(
                name="url",
                required=True,
                type=OpenApiTypes.URI,
                description=_("URL reference of ZAAK EIGENSCHAP in ZAKEN API"),
                location=OpenApiParameter.QUERY,
            )
        ],
    )
    def delete(self, request, *args, **kwargs):
        zaak_eigenschap = self.get_object()
        delete_zaak_eigenschap(zaak_eigenschap.url)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RelatedZakenView(GetZaakMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanReadZaken,)
    serializer_class = RelatedZaakSerializer
    schema_summary = _("List related cases")

    def get(self, request, *args, **kwargs):
        zaak = self.get_object()
        related_zaken = [
            {
                "aard_relatie": aard_relatie,
                "zaak": zaak,
            }
            for aard_relatie, zaak in get_related_zaken(zaak)
        ]

        serializer = self.serializer_class(instance=related_zaken, many=True)
        return Response(serializer.data)


@extend_schema(summary=_("Add related zaak"))
class CreateZaakRelationView(views.APIView):
    permission_classes = (permissions.IsAuthenticated, CanAddRelations)

    def get_serializer(self, *args, **kwargs):
        return AddZaakRelationSerializer(data=self.request.data)

    def post(self, request: Request) -> Response:
        serializer = self.get_serializer()
        serializer.is_valid(raise_exception=True)

        # Retrieving the main zaak
        zaak_url = serializer.validated_data["main_zaak"]
        client = Service.get_client(zaak_url)
        main_zaak = client.retrieve("zaak", url=zaak_url)

        main_zaak["relevanteAndereZaken"].append(
            {
                "url": serializer.validated_data["relation_zaak"],
                "aardRelatie": serializer.validated_data["aard_relatie"],
            }
        )

        # Create the relation
        client.partial_update(
            "zaak",
            {"relevanteAndereZaken": main_zaak["relevanteAndereZaken"]},
            url=zaak_url,
        )

        invalidate_zaak_cache(factory(Zaak, main_zaak))

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ZaakRolesView(GetZaakMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanReadZaken,)
    serializer_class = RolSerializer
    schema_summary = _("List case roles")

    def get(self, request, *args, **kwargs):
        zaak = self.get_object()
        rollen = get_rollen(zaak)
        serializer = self.serializer_class(instance=rollen, many=True)
        return Response(serializer.data)


class ZaakObjectsView(GetZaakMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanReadZaken,)
    serializer_class = ZaakObjectGroupSerializer
    schema_summary = _("List related objects of a case")

    def get(self, request, *args, **kwargs):
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
            groups.append(group)

        serializer = self.serializer_class(instance=groups, many=True)
        return Response(serializer.data)


class ZaakAtomicPermissionsView(GetZaakMixin, ListAPIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanHandleAccessRequests,)
    serializer_class = UserAtomicPermissionSerializer
    schema_summary = _("List case users and atomic permissions")

    def get_queryset(self):
        zaak = self.get_object()

        queryset = (
            User.objects.filter(atomic_permissions__object_url=zaak.url)
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
        return queryset


###############################
#          Documents          #
###############################


@extend_schema(summary=_("List case documents"))
class ListZaakDocumentsView(GetZaakMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanReadZaken,)
    serializer_class = GetZaakDocumentSerializer

    def get(self, request, *args, **kwargs):
        zaak = self.get_object()
        documents, gone = get_documenten(zaak)
        filtered_documenten = filter_documenten_for_permissions(documents, request)
        resolved_documenten = resolve_documenten_informatieobjecttypen(
            filtered_documenten
        )
        referer = request.headers.get("referer", "")
        open_documenten = get_open_documenten(request.user, referer)

        serializer = self.serializer_class(
            instance=resolved_documenten,
            many=True,
            context={"open_documenten": [dowc.drc_url for dowc in open_documenten]},
        )
        return Response(serializer.data)


class ZaakDocumentView(views.APIView):
    permission_classes = (
        permissions.IsAuthenticated & CanAddOrUpdateZaakDocuments & CanUpdateZaken,
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
                }
            )

        document_data = {**document_data, **validated_data}
        return document_data

    @extend_schema(
        summary=_("Edit case document"),
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

        zaak = get_zaak(zaak_url=serializer.validated_data["zaak"])
        document_data = self.get_document_data(serializer.validated_data, zaak)
        try:
            document = update_document(document_url, document_data, audit_line)
        except ClientError as err:
            raise APIException(err.args[0])

        document.informatieobjecttype = get_informatieobjecttype(
            document.informatieobjecttype
        )
        serializer = GetZaakDocumentSerializer(instance=document)
        return Response(serializer.data)

    @extend_schema(
        summary=_("Add document to case"),
        responses=GetZaakDocumentSerializer,
    )
    def post(self, request: Request, *args, **kwargs) -> Response:
        """
        Upload a document to the Documenten API and relate it to a case.
        """
        serializer = self.get_serializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        zaak = get_zaak(zaak_url=serializer.validated_data["zaak"])
        document_data = self.get_document_data(serializer.validated_data, zaak)
        document = create_document(document_data)
        relate_document_to_zaak(document.url, zaak.url)
        document.informatieobjecttype = get_informatieobjecttype(
            document.informatieobjecttype
        )
        serializer = GetZaakDocumentSerializer(instance=document)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


###############################
#  META / Catalogi API views  #
###############################


@extend_schema(
    summary=_("List document types"),
    tags=["meta"],
    parameters=[
        OpenApiParameter(
            name="zaak",
            required=True,
            type=OpenApiTypes.URI,
            description=_("Zaak to list available document types for"),
            location=OpenApiParameter.QUERY,
        )
    ],
)
class InformatieObjectTypeListView(generics.ListAPIView):
    """
    List the available document types for a given zaak.

    TODO: permissions checks on zaak - can this user read/mutate the zaak?
    """

    serializer_class = InformatieObjectTypeSerializer
    filter_backends = ()

    def get_queryset(self):
        zaak_url = self.request.query_params.get("zaak")
        if not zaak_url:
            raise exceptions.ValidationError("'zaak' query parameter is required.")
        return get_informatieobjecttypen_for_zaak(zaak_url)


@extend_schema(summary=_("List zaaktypen"), tags=["meta"])
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
        zaaktypen = get_zaaktypen(self.request.user)

        # aggregate
        zaaktypen_data = [
            {
                "catalogus": zaaktype.catalogus,
                "identificatie": zaaktype.identificatie,
                "omschrijving": zaaktype.omschrijving,
            }
            for zaaktype in zaaktypen
        ]
        zaaktypen_aggregated = {
            frozenset(zaaktype.items()): zaaktype for zaaktype in zaaktypen_data
        }.values()
        zaaktypen_aggregated = sorted(
            zaaktypen_aggregated, key=lambda z: (z["catalogus"], z["omschrijving"])
        )
        return zaaktypen_aggregated


@extend_schema(summary=_("List confidentiality classifications"), tags=["meta"])
class VertrouwelijkheidsAanduidingenView(ListAPIView):
    """
    List the available confidentiality classification.
    """

    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = VertrouwelijkheidsAanduidingSerializer

    def get_queryset(self):
        return [
            VertrouwelijkheidsAanduidingData(label=choice[1], value=choice[0])
            for choice in VertrouwelijkheidsAanduidingen.choices
        ]


@extend_schema(
    summary=_("List statustypes"),
    tags=["meta"],
    parameters=[
        OpenApiParameter(
            name="zaak",
            required=True,
            type=OpenApiTypes.URI,
            description=_("Zaak to list available statustypes for"),
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
            raise exceptions.ValidationError("'zaak' query parameter is required.")
        zaak = get_zaak(zaak_url=zaak_url)
        zaaktype = fetch_zaaktype(zaak.zaaktype)
        statusstypen = get_statustypen(zaaktype)
        serializer = self.serializer_class(statusstypen, many=True)
        return Response(serializer.data)


@extend_schema(summary=_("List zaaktype eigenschappen"), tags=["meta"])
class EigenschappenView(ListAPIView):
    """
    List the available eigenschappen for a given zaaktype.

    Given the `zaaktype_omschrijving`, all versions of the matching zaaktype are
    considered. Returns the eigenschappen available for the aggregated set of zaaktype
    versions.

    Note that only the zaaktypen that the authenticated user has read-permissions for
    are considered.
    """

    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = SearchEigenschapSerializer
    filter_backends = (ApiFilterBackend,)
    filterset_class = EigenschappenFilterSet

    def list(self, request, *args, **kwargs):
        # validate query params
        filterset = self.filterset_class(
            data=self.request.query_params, request=self.request
        )
        if not filterset.is_valid():
            raise exceptions.ValidationError(filterset.errors)

        zaaktypen = self.get_zaaktypen()
        eigenschappen = self.get_eigenschappen(zaaktypen)

        serializer = self.get_serializer(eigenschappen, many=True)
        return Response(serializer.data)

    def get_zaaktypen(self):
        catalogus = self.request.query_params.get("catalogus")
        zaaktype_omschrijving = self.request.query_params.get("zaaktype_omschrijving")

        return get_zaaktypen(
            self.request.user,
            catalogus=catalogus,
            omschrijving=zaaktype_omschrijving,
        )

    def get_eigenschappen(self, zaaktypen):
        with parallel() as executor:
            _eigenschappen = executor.map(get_eigenschappen, zaaktypen)

        eigenschappen = sum(list(_eigenschappen), [])

        # transform values and remove duplicates
        eigenschappen_aggregated = []
        for eigenschap in eigenschappen:
            eigenschap_data = {
                "name": eigenschap.naam,
                "spec": convert_eigenschap_spec_to_json_schema(eigenschap.specificatie),
            }

            existing_eigenschappen = [
                e
                for e in eigenschappen_aggregated
                if e["name"] == eigenschap_data["name"]
            ]
            if existing_eigenschappen:
                if eigenschap_data["spec"] != existing_eigenschappen[0]["spec"]:
                    logger.warning(
                        "Eigenschappen '%(name)s' which belong to zaaktype '%(zaaktype)s' have different specs"
                        % {
                            "name": eigenschap.naam,
                            "zaaktype": eigenschap.zaaktype.omschrijving,
                        }
                    )
                continue

            eigenschappen_aggregated.append(eigenschap_data)

        eigenschappen_aggregated = sorted(
            eigenschappen_aggregated, key=lambda e: e["name"]
        )

        return eigenschappen_aggregated


#
# Objects endpoints
#


@extend_schema(
    summary=_("List objecttypes"),
    description=_("Retrieves all object types from the configured Objecttypes API."),
    tags=["objects"],
)
class ObjecttypeListView(ListMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ObjecttypeProxySerializer
    action = "list"

    def get_objects(self) -> List[dict]:
        return fetch_objecttypes()


@extend_schema(
    summary=_("Read objecttype version"),
    description=_("Read the details of a particular objecttype version"),
    tags=["objects"],
)
class ObjecttypeVersionReadView(RetrieveMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ObjecttypeVersionProxySerializer

    def get_object(self) -> dict:
        return fetch_objecttype_version(**self.kwargs)


@extend_schema(
    summary=_("Search objects"),
    description=_("Search for objects in the Objects API"),
    responses={(200, "application/json"): ObjectProxySerializer},
    tags=["objects"],
)
class ObjectSearchView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ObjectFilterProxySerializer

    def post(self, request):
        try:
            objects = search_objects(filters=request.data)
        except ClientError as exc:
            raise ValidationError(detail=exc.args)

        object_serializer = ObjectProxySerializer(objects, many=True)
        return Response(object_serializer.data)


class ZaakObjectChangeView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated, CanUpdateZaken)
    serializer_class = ZaakObjectProxySerializer
    filterset_class = ZaakObjectFilterSet

    def get_object(self):
        filterset = self.filterset_class(
            data=self.request.query_params, request=self.request
        )
        if not filterset.is_valid():
            raise exceptions.ValidationError(filterset.errors)
        url = self.request.query_params.get("url")

        try:
            zaak_object = fetch_zaak_object(url)
        except ClientError as exc:
            raise Http404("No zaak object matches the given url.")

        # check permissions
        zaak = get_zaak(zaak_url=zaak_object.zaak)
        self.check_object_permissions(self.request, zaak)

        return zaak_object

    @extend_schema(
        summary=_("Create zaakobject"),
        description=_("Relate an object to a zaak"),
        responses={(201, "application/json"): ZaakObjectProxySerializer},
        tags=["objects"],
    )
    def post(self, request):
        # check permissions
        zaak_url = request.data["zaak"]
        zaak = get_zaak(zaak_url=zaak_url)
        self.check_object_permissions(self.request, zaak)

        try:
            created_zaakobject = relate_object_to_zaak(request.data)
        except ClientError as exc:
            raise ValidationError(detail=exc.args)

        return Response(status=201, data=created_zaakobject)

    @extend_schema(
        summary=_("Delete zaak object"),
        parameters=[
            OpenApiParameter(
                name="url",
                required=True,
                type=OpenApiTypes.URI,
                description=_("URL reference of ZAAK OBJECT in ZAKEN API"),
                location=OpenApiParameter.QUERY,
            )
        ],
        tags=["objects"],
    )
    def delete(self, request, *args, **kwargs):
        zaak_object = self.get_object()
        delete_zaak_object(zaak_object.url)
        return Response(status=status.HTTP_204_NO_CONTENT)
