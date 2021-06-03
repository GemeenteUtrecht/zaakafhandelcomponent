from django.http import JsonResponse
from django.utils.translation import ugettext_lazy as _

from drf_spectacular.utils import extend_schema
from rest_framework import generics, views
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated

from zac.accounts.api.serializers import CatalogusURLSerializer
from zac.core.services import get_informatieobjecttypen

from .permissions import CanHandleAccess
from .serializers import GrantPermissionSerializer


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


@extend_schema(summary=_("Grant permission to zaak"))
class GrantZaakPermissionView(generics.CreateAPIView):
    """
    Create an atomic permission for a particular user
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, CanHandleAccess]
    serializer_class = GrantPermissionSerializer
