import base64
from datetime import date

from rest_framework import exceptions, status, views
from rest_framework.request import Request
from rest_framework.response import Response
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from ..services import get_zaak
from .serializers import (
    AddDocumentResponseSerializer,
    AddDocumentSerializer,
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
            "auteur": request.user.get_full_name()
            or request.user.username,  # TODO: take user input
            "taal": "nld",
            "inhoud": str(inhoud),  # it's base64, so ascii compatible
            "formaat": uploaded_file.content_type,
            "bestandsnaam": uploaded_file.name,
            "ontvangstdatum": date.today().isoformat(),
        }

        services = Service.objects.filter(api_type=APITypes.drc)
        service = services.first()  # TODO: config option to select the default?
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
