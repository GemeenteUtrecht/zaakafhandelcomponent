from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.zaken import Zaak

from zac.activities.models import Activity
from zac.core.cache import invalidate_zaak_cache, invalidate_zaak_list_cache
from zac.core.services import _client_from_url
from zac.elasticsearch.api import (
    create_zaak_document,
    delete_zaak_document,
    update_rollen_in_zaak_document,
    update_zaak_document,
)

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

        if data["resource"] == "zaak":
            if data["actie"] == "create":
                self._handle_zaak_creation(data["hoofd_object"])
            elif data["actie"] in ["update", "partial_update"]:
                self._handle_zaak_update(data["hoofd_object"])
            elif data["actie"] == "destroy":
                self._handle_zaak_destroy(data["hoofd_object"])
        elif (
            data["resource"] in ["resultaat", "status", "zaakeigenschap"]
            and data["actie"] == "create"
        ):
            self._handle_related_creation(data["hoofd_object"])

        elif data["resource"] == "rol":
            self._handle_rol_change(data["hoofd_object"])

    @staticmethod
    def _retrieve_zaak(zaak_url) -> Zaak:
        client = _client_from_url(zaak_url)
        zaak = client.retrieve("zaak", url=zaak_url)
        return factory(Zaak, zaak)

    def _handle_zaak_update(self, zaak_url: str):
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaak_cache(zaak)
        # index in ES
        update_zaak_document(zaak)

    def _handle_zaak_creation(self, zaak_url: str):
        client = _client_from_url(zaak_url)
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaak_list_cache(client, zaak)
        # index in ES
        create_zaak_document(zaak)

    def _handle_zaak_destroy(self, zaak_url: str):
        Activity.objects.filter(zaak=zaak_url).delete()
        # index in ES
        delete_zaak_document(zaak_url)

    def _handle_related_creation(self, zaak_url):
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaak_cache(zaak)

    def _handle_rol_change(self, zaak_url):
        zaak = self._retrieve_zaak(zaak_url)
        # index in ES
        update_rollen_in_zaak_document(zaak)
