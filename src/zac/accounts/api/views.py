from django.http import JsonResponse

from rest_framework import views
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from zac.accounts.api.serializers import CatalogusURLSerializer
from zac.core.services import get_informatieobjecttypen


class InformatieobjecttypenJSONView(views.APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return the informatieobjecttypen for a catalogus"""
        catalogus_url_serializer = CatalogusURLSerializer(
            data={"url": request.GET.get("catalogus")}
        )
        if not catalogus_url_serializer.is_valid():
            raise ValidationError

        informatieobjecttypen = get_informatieobjecttypen(
            catalogus=catalogus_url_serializer.validated_data["url"]
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
