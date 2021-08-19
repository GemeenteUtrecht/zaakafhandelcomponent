from django.http import JsonResponse
from django.utils.translation import ugettext_lazy as _

from drf_spectacular.utils import extend_schema
from rest_framework import views
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from zac.core.services import get_informatieobjecttypen

from ..permissions import registry
from .serializers import CatalogusURLSerializer, PermissionSerializer


class InformatieobjecttypenJSONView(views.APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    schema = None

    def get(self, request):
        """Return the informatieobjecttypen for a catalogus"""
        catalogus_url_serializer = CatalogusURLSerializer(
            data={"url": request.GET.get("catalogus")}
        )
        catalogus_url_serializer.is_valid(raise_exception=True)

        informatieobjecttypen = get_informatieobjecttypen(
            catalogus=catalogus_url_serializer.validated_data["url"]
        )
        informatieobjecttypen = sorted(
            informatieobjecttypen, key=lambda iot: iot.omschrijving.lower()
        )

        response_data = {"formData": [], "emptyFormData": []}
        for informatieobjecttype in informatieobjecttypen:
            response_data["emptyFormData"].append(
                {
                    "catalogus": catalogus_url_serializer.validated_data["url"],
                    "omschrijving": informatieobjecttype.omschrijving,
                    "selected": False,
                }
            )
        return JsonResponse(response_data)


class PermissionView(views.APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = PermissionSerializer

    @extend_schema(
        summary=_("List permissions"), responses={200: serializer_class(many=True)}
    )
    def get(self, request):
        """Return all available permissions and their description"""
        permissions = list(registry.values())
        serializer = self.serializer_class(permissions, many=True)
        return Response(serializer.data)
