import base64
import logging
from datetime import date
from itertools import groupby
from typing import Dict, List

from django.core.exceptions import ObjectDoesNotExist
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
from rest_framework.exceptions import APIException
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from zds_client.client import ClientError
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.concurrent import parallel
from zgw_consumers.models import Service

from zac.contrib.brp.api import fetch_extrainfo_np
from zac.contrib.kownsl.api import get_review_requests, retrieve_advices
from zac.core.services import update_document
from zac.utils.filters import ApiFilterBackend
from zgw.models.zrc import Zaak

from ..cache import invalidate_zaak_cache
from ..services import (
    create_document,
    find_zaak,
    get_document,
    get_documenten,
    get_eigenschappen,
    get_informatieobjecttype,
    get_related_zaken,
    get_resultaat,
    get_rollen,
    get_statussen,
    get_zaak,
    get_zaak_eigenschappen,
    get_zaakobjecten,
    get_zaaktypen,
    relate_document_to_zaak,
)
from ..views.utils import filter_documenten_for_permissions, get_source_doc_versions
from ..zaakobjecten import GROUPS, ZaakObjectGroup
from .data import VertrouwelijkheidsAanduidingData
from .filters import EigenschappenFilterSet, ZaaktypenFilterSet
from .pagination import BffPagination
from .permissions import (
    CanAddOrUpdateZaakDocuments,
    CanAddRelations,
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
    RelatedZaakSerializer,
    RolSerializer,
    SearchEigenschapSerializer,
    UpdateZaakDetailSerializer,
    UpdateZaakDocumentSerializer,
    VertrouwelijkheidsAanduidingSerializer,
    ZaakDetailSerializer,
    ZaakEigenschapSerializer,
    ZaakObjectGroupSerializer,
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

    def create_permission_message(self, request):
        """
        Add custom permission body, since we use AND and can't set it inside permission classes
        """
        return {"can_request_access": True, "reason": ""}

    def permission_denied(self, request, message=None, code=None):

        message = message or self.create_permission_message(request)

        if request.authenticators and not request.successful_authenticator:
            raise exceptions.NotAuthenticated()
        raise exceptions.PermissionDenied(detail=message, code=code)


class ZaakStatusesView(GetZaakMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanReadZaken,)
    serializer_class = ZaakStatusSerializer
    schema_summary = _("List case statuses")

    def get(self, request, *args, **kwargs):
        zaak = self.get_object()
        statussen = get_statussen(zaak)
        serializer = self.serializer_class(instance=statussen, many=True)
        return Response(serializer.data)


class ZaakEigenschappenView(GetZaakMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanReadZaken,)
    serializer_class = ZaakEigenschapSerializer
    schema_summary = _("List case properties (eigenschappen)")

    def get(self, request, *args, **kwargs):
        zaak = self.get_object()
        eigenschappen = get_zaak_eigenschappen(zaak)
        serializer = self.serializer_class(instance=eigenschappen, many=True)
        return Response(serializer.data)


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
        zaakobjecten = get_zaakobjecten(zaak.url)

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
                _group, ZaakObjectGroup(object_type=_group, label=_group)
            )
            group.retrieve_items(items)
            groups.append(group)

        serializer = self.serializer_class(instance=groups, many=True)
        return Response(serializer.data)


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

        review_requests = get_review_requests(zaak)

        with parallel() as executor:
            _advices = executor.map(
                lambda rr: retrieve_advices(rr) if rr else [],
                [rr if rr.num_advices else None for rr in review_requests],
            )

            for rr, rr_advices in zip(review_requests, _advices):
                rr.advices = rr_advices

        doc_versions = get_source_doc_versions(review_requests)
        documents, gone = get_documenten(zaak, doc_versions)
        filtered_documenten = filter_documenten_for_permissions(documents, request)

        serializer = self.serializer_class(
            instance=filtered_documenten,
            many=True,
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
