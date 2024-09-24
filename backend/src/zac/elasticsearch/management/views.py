from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.http import Http404
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.views import APIView

from zac.core.services import find_zaak

from .constants import IndexTypes
from .serializers import ManageIndexSerializer, ReindexZaakSerializer


class IndexElasticsearchView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (
        IsAuthenticated,
        IsAdminUser,
    )

    @extend_schema(
        summary=_("Index Elasticsearch."),
        request=ManageIndexSerializer,
        responses={204: None},
        tags=["management"],
    )
    def post(self, request):
        serializer = ManageIndexSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        args = [serializer.data["index"]]

        args.append(f'--chunk-size={serializer.validated_data["chunk_size"]}')
        args.append(f'--max-workers={serializer.validated_data["max_workers"]}')

        if reindex_last := serializer.validated_data.get("reindex_last"):
            args.append(f"--reindex-last={reindex_last}")

        if reindex_zaak := serializer.validated_data.get("reindex_zaak"):
            args.append(f"--reindex-zaak={reindex_zaak.url}")

        call_command(*args)
        return Response(status=HTTP_204_NO_CONTENT)


class ReIndexZaakElasticsearchView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (
        IsAuthenticated,
        IsAdminUser,
    )

    @extend_schema(
        "search_management_reindex_zaak_create",
        summary=_("Reindex ZAAK in Elasticsearch."),
        request=ReindexZaakSerializer,
        responses={204: None},
        tags=["management"],
    )
    def post(self, request, bronorganisatie, identificatie):
        try:
            zaak = find_zaak(
                bronorganisatie=bronorganisatie, identificatie=identificatie
            )
        except ObjectDoesNotExist:
            raise Http404("No ZAAK matches the given query.")

        serializer = ReindexZaakSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        args = [IndexTypes.index_all]

        args.append(f'--chunk-size={serializer.validated_data["chunk_size"]}')
        args.append(f'--max-workers={serializer.validated_data["max_workers"]}')

        args.append(f"--reindex-zaak={zaak.url}")

        call_command(" ".join(args))
        return Response(status=HTTP_204_NO_CONTENT)
