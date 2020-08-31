import base64
from datetime import date

from rest_framework import exceptions, status, views
from rest_framework.request import Request
from rest_framework.response import Response
from zgw_consumers.models import Service

from zac.contrib.brp.api import fetch_extrainfo_np

from ..models import CoreConfig
from ..services import get_document, get_informatieobjecttype, get_zaak
from .serializers import (
    AddDocumentResponseSerializer,
    AddDocumentSerializer,
    DocumentInfoSerializer,
    ExtraInfoSubjectSerializer,
    InformatieObjectTypeSerializer,
)
from .utils import get_informatieobjecttypen_for_zaak


class GetInformatieObjectTypenView(views.APIView):

    # TODO: permissions checks on zaak - can this user read/mutate the zaak?

    def get(self, request: Request) -> Response:
        zaak_url = request.query_params.get("zaak")
        if not zaak_url:
            raise exceptions.ValidationError("'zaak' query parameter is required.")

        informatieobjecttypen = get_informatieobjecttypen_for_zaak(zaak_url)

        serializer = InformatieObjectTypeSerializer(informatieobjecttypen, many=True)
        return Response(serializer.data)


class AddDocumentView(views.APIView):

    # TODO: permissions checks on zaak - can this user add documents to the zaak?

    def post(self, request: Request) -> Response:
        serializer = AddDocumentSerializer(data=request.data)
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
            {"informatieobject": document["url"], "zaak": zaak.url,},
        )

        response_serializer = AddDocumentResponseSerializer(document)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class GetDocumentInfoView(views.APIView):
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


class GetExtraInfoSubjectView(views.APIView):
    def get(self, request: Request, **kwargs) -> Response:
        error_messages = []

        # Check if doelbinding is given and valid
        doelbinding = request.query_params.get("doelbinding")
        if not doelbinding or len(doelbinding) == 0:
            error_messages.append("Doelbinding is vereist.")

        # Check if fields query parameter is given...
        fields = request.query_params.get("fields")
        if not fields or len(fields) == 0:
            error_messages.append("Een extra-informatie veld is vereist.")

        # ... and if they are valid.
        elif fields:
            fields_set = set([_.lower() for _ in fields.split(",")])
            valid_choices = set(
                [
                    "geboorte.datum",
                    "geboorte.land",
                    "verblijfplaats",
                    "kinderen",
                    "partners",
                ]
            )

            # Feedback why they're not valid
            if not fields_set.issubset(valid_choices):
                not_valid_fields = list(fields_set - valid_choices)
                error_messages.append(
                    "Veld(en): {}, zijn niet geldig.".format(
                        ", ".join(not_valid_fields)
                    )
                )
        # Feedback errors
        if len(error_messages) > 0:
            return Response(
                {"Errors": " ".join(error_messages)}, status=status.HTTP_400_BAD_REQUEST
            )

        # Get bsn kwarg
        bsn = kwargs.get("bsn")

        # Get extra info
        extra_info_inp = fetch_extrainfo_np(bsn, request.query_params)
        serializer = ExtraInfoSubjectSerializer(extra_info_inp)
        return Response(serializer.data)
