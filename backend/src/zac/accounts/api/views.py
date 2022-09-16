from django.contrib.auth import logout
from django.http import JsonResponse
from django.utils.translation import ugettext_lazy as _

from drf_spectacular.utils import extend_schema
from rest_framework import status, views
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from zac.core.api.mixins import ListMixin
from zac.core.services import get_informatieobjecttypen

from ..utils import permissions_related_to_user
from .serializers import CatalogusURLSerializer, PermissionSerializer


class InformatieobjecttypenJSONView(views.APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    schema = None

    def get(self, request):
        """Returns the informatieobjecttypen for a catalogus"""
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


@extend_schema(
    summary=_("List permissions."),
    description=_(
        "Returns all available permissions for the user and their description."
    ),
)
class PermissionView(ListMixin, views.APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = PermissionSerializer

    def get_objects(self):
        """
        Only returns permissions the user has.

        """
        perms = permissions_related_to_user(self.request)
        return perms


@extend_schema(
    summary=_("Logout user."),
    description=_("Logs the current user out."),
    responses={
        "204": None,
    },
)
class LogoutView(views.APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_serializer(self, *args, **kwargs):
        # Shut up drf-spectacular - return empty serializer
        return {}

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
