from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from zac.core.cache import invalidate_zaak_list_cache
from zac.core.services import _client_from_url

from .serializers import NotificatieSerializer


class NotificationCallbackView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = NotificatieSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.handle_notification(serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def handle_notification(self, data: dict):
        if not data["kanaal"] == "zaken":
            return

        if data["resource"] == "zaak" and data["actie"] == "create":
            self._handle_zaak_creation(data["hoofd_object"])

    def _handle_zaak_creation(self, zaak_url: str):
        client = _client_from_url(zaak_url)
        zaak = client.retrieve("zaak", url=zaak_url)
        invalidate_zaak_list_cache(client, zaak)
