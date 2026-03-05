from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.http import Http404
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.views import APIView

from zac.accounts.api.permissions import HasTokenAuth
from zac.accounts.authentication import ApplicationTokenAuthentication
from zac.core.services import find_zaak

from .constants import IndexTypes
from .serializers import ManageIndexSerializer, ReindexZaakSerializer


class FixVAOrderSerializer(serializers.Serializer):
    dry_run = serializers.BooleanField(
        required=False,
        default=False,
        help_text=_("Only show what would be updated without making changes."),
    )


class FixVAOrderView(APIView):
    authentication_classes = (ApplicationTokenAuthentication, TokenAuthentication)
    permission_classes = (
        HasTokenAuth | IsAuthenticated,
        IsAdminUser,
    )

    @extend_schema(
        summary=_("Fix va_order mapping in Elasticsearch."),
        description=_(
            "Recalculates va_order in ES from vertrouwelijkheidaanduiding using update_by_query."
        ),
        request=FixVAOrderSerializer,
        responses={200: serializers.ListField(child=serializers.CharField())},
        tags=["management"],
    )
    def post(self, request):
        import io
        import sys

        from django.core.management import call_command

        serializer = FixVAOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        out = io.StringIO()
        args = ["fix_va_order"]
        if serializer.validated_data.get("dry_run"):
            args.append("--dry-run")

        old_stdout = sys.stdout
        sys.stdout = out
        try:
            call_command(*args, stdout=out, stderr=out)
        finally:
            sys.stdout = old_stdout

        output_lines = [line for line in out.getvalue().split("\n") if line]
        return Response(data=output_lines)


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

        call_command(*args)
        return Response(status=HTTP_204_NO_CONTENT)
