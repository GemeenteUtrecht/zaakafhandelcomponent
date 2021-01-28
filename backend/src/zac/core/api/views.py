import base64
from datetime import date
from itertools import groupby

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect

from rest_framework import authentication, exceptions, permissions, status, views
from rest_framework.request import Request
from rest_framework.response import Response
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.zaken import Zaak
from zgw_consumers.concurrent import parallel
from zgw_consumers.models import Service

from zac.contrib.brp.api import fetch_extrainfo_np
from zac.contrib.kownsl.api import get_review_requests, retrieve_advices
from zac.elasticsearch.searches import autocomplete_zaak_search

from ..cache import invalidate_zaak_cache
from ..models import CoreConfig
from ..services import (
    find_zaak,
    get_document,
    get_documenten,
    get_informatieobjecttype,
    get_related_zaken,
    get_rollen,
    get_statussen,
    get_zaak,
    get_zaak_eigenschappen,
    get_zaakobjecten,
)
from ..views.utils import filter_documenten_for_permissions, get_source_doc_versions
from ..zaakobjecten import GROUPS, ZaakObjectGroup
from .permissions import CanAddDocuments, CanAddRelations, CanReadZaken
from .serializers import (
    AddDocumentResponseSerializer,
    AddDocumentSerializer,
    AddZaakRelationSerializer,
    DocumentInfoSerializer,
    ExpandParamSerializer,
    ExtraInfoSubjectSerializer,
    ExtraInfoUpSerializer,
    InformatieObjectTypeSerializer,
    RelatedZaakSerializer,
    RolSerializer,
    ZaakDetailSerializer,
    ZaakDocumentSerializer,
    ZaakEigenschapSerializer,
    ZaakIdentificatieSerializer,
    ZaakObjectGroupSerializer,
    ZaakSerializer,
    ZaakStatusSerializer,
)
from .utils import get_informatieobjecttypen_for_zaak


class GetInformatieObjectTypenView(views.APIView):
    schema = None

    # TODO: permissions checks on zaak - can this user read/mutate the zaak?

    def get(self, request: Request) -> Response:
        zaak_url = request.query_params.get("zaak")
        if not zaak_url:
            raise exceptions.ValidationError("'zaak' query parameter is required.")

        informatieobjecttypen = get_informatieobjecttypen_for_zaak(zaak_url)

        serializer = InformatieObjectTypeSerializer(informatieobjecttypen, many=True)
        return Response(serializer.data)


class AddDocumentView(views.APIView):
    permission_classes = (permissions.IsAuthenticated, CanAddDocuments)
    schema = None

    def get_serializer(self, *args, **kwargs):
        return AddDocumentSerializer(data=self.request.data)

    def post(self, request: Request) -> Response:
        serializer = self.get_serializer()
        serializer.is_valid(raise_exception=True)

        # create the document
        zaak = get_zaak(zaak_url=serializer.validated_data["zaak"])

        uploaded_file = serializer.validated_data["file"]

        with uploaded_file.open("rb") as content:
            inhoud = base64.b64encode(content.read())

        document_data = {
            "informatieobjecttype": serializer.validated_data["informatieobjecttype"],
            "bronorganisatie": zaak.bronorganisatie,  # TODO: what if it's different?
            "creatiedatum": date.today().isoformat(),  # TODO: what if it's created on another date
            "titel": uploaded_file.name,
            # TODO: take user input
            "auteur": request.user.get_full_name() or request.user.username,
            "taal": "nld",
            "inhoud": str(inhoud),  # it's base64, so ascii compatible
            "formaat": uploaded_file.content_type,
            "bestandsnaam": uploaded_file.name,
            "ontvangstdatum": date.today().isoformat(),
            # "beschrijving": serializer.validated_data.get("beschrijving", ""),
        }

        core_config = CoreConfig.get_solo()
        service = core_config.primary_drc
        if not service:
            raise RuntimeError("No DRC configured!")

        drc_client = service.build_client()

        document = drc_client.create("enkelvoudiginformatieobject", document_data)

        # relate document and zaak
        zrc_client = Service.get_client(
            zaak.url
        )  # resolves, otherwise the get_zaak would've failed
        zrc_client.create(
            "zaakinformatieobject",
            {
                "informatieobject": document["url"],
                "zaak": zaak.url,
            },
        )

        response_serializer = AddDocumentResponseSerializer(document)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class GetDocumentInfoView(views.APIView):
    schema = None

    def get(self, request: Request) -> Response:
        document_url = request.query_params.get("document")
        if not document_url:
            raise exceptions.ValidationError("'document' query parameter is required.")

        document = get_document(url=document_url)
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


class AddZaakRelationView(views.APIView):
    permission_classes = (permissions.IsAuthenticated, CanAddRelations)
    schema = None

    def get_serializer(self, *args, **kwargs):
        return AddZaakRelationSerializer(data=self.request.data)

    def post(self, request: Request) -> Response:
        serializer = self.get_serializer()
        serializer.is_valid(raise_exception=True)

        # Retrieving the main zaak
        client = Service.get_client(serializer.validated_data["main_zaak"])
        main_zaak = client.retrieve("zaak", url=serializer.validated_data["main_zaak"])

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
            url=serializer.validated_data["main_zaak"],
        )

        invalidate_zaak_cache(factory(Zaak, main_zaak))

        return Response(status=status.HTTP_200_OK)


class GetZakenView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)
    schema = None

    def get(self, request: Request) -> Response:
        serializer = ZaakIdentificatieSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        zaken = autocomplete_zaak_search(
            identificatie=serializer.validated_data["identificatie"]
        )
        zaak_serializer = ZaakSerializer(instance=zaken, many=True)
        return Response(data=zaak_serializer.data)


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
    permission_classes = (permissions.IsAuthenticated & CanReadZaken,)
    serializer_class = ZaakDetailSerializer
    schema_summary = _("Retrieve case details")

    def get(self, request, *args, **kwargs):
        zaak = self.get_object()
        serializer = self.serializer_class(instance=zaak)
        return Response(serializer.data)


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


class ZaakDocumentsView(GetZaakMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanReadZaken,)
    serializer_class = ZaakDocumentSerializer
    schema_summary = _("List case documents")

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
        filtered_documenten = filter_documenten_for_permissions(documents, request.user)

        serializer = self.serializer_class(
            instance=filtered_documenten, many=True, context={"request": request}
        )
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
