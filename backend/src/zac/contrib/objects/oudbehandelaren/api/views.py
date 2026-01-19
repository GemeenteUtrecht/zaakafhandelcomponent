from django.http import Http404
from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, views
from rest_framework.response import Response

from zac.contrib.objects.services import fetch_oudbehandelaren
from zac.core.api.permissions import CanReadZaken
from zac.core.services import find_zaak

from ..data import Oudbehandelaren
from .serializers import OudbehandelarenSerializer


class OudbehandelarenView(views.APIView):
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadZaken,
    )
    serializer_class = OudbehandelarenSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **kwargs)

    def get_object(self) -> Oudbehandelaren:
        bronorganisatie = self.request.parser_context["kwargs"]["bronorganisatie"]
        identificatie = self.request.parser_context["kwargs"]["identificatie"]
        zaak = find_zaak(bronorganisatie, identificatie)
        if not (oudbehandelaren := fetch_oudbehandelaren(zaak)):
            raise Http404("`oudbehandelaren` not found for ZAAK.")

        self.check_object_permissions(self.request, zaak)
        return oudbehandelaren

    @extend_schema(
        summary=_("Retrieve `oudbehandelaren` for ZAAK."),
        parameters=[
            OpenApiParameter(
                name="bronorganisatie",
                required=True,
                type=OpenApiTypes.STR,
                description=_("Bronorganisatie of the ZAAK."),
                location=OpenApiParameter.PATH,
            ),
            OpenApiParameter(
                name="identificatie",
                required=True,
                type=OpenApiTypes.STR,
                description=_("Identificatie of the ZAAK."),
                location=OpenApiParameter.PATH,
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        oudbehandelaren = self.get_object()
        return Response(self.get_serializer(oudbehandelaren).data)
