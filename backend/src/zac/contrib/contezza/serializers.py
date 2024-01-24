from typing import Dict, Union

import furl
from rest_framework import serializers
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.core.services import client_from_object
from zac.elasticsearch.documents import InformatieObjectDocument

from .constants import ContezzaDocumentTypes

CONTEZZA_PAYLOAD_MAPPING = {
    "edit": {
        "actionNodeRef": "workspace://SpacesStore/{uuid}",
        "actionType": "createDriveItem",
    },
    "resume": {
        "actionNodeRef": "workspace://SpacesStore/{uuid}",
        "actionType": "resumeEditDriveItem",
    },
    "cancel": {
        "actionNodeRef": "workspace://SpacesStore/{uuid}",
        "actionType": "cancelEditDriveItem",
    },
    "check_in": {
        "actionNodeRef": "workspace://SpacesStore/{uuid}",
        "actionType": "checkInDeleteDriveItem",
    },
}

CONTEZZA_URL_MAPPING = {}


class ContezzaDocumentSerializer(APIModelSerializer):
    action = serializers.ChoiceField(
        choices=ContezzaDocumentTypes.choices, required=True
    )
    contezza_payload = serializers.SerializerMethodField()
    contezza_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ("action", "contezza_payload", "contezza_url")

    def get_contezza_payload(
        self, obj: Union[Document, InformatieObjectDocument]
    ) -> Dict[str, str]:
        payload = CONTEZZA_PAYLOAD_MAPPING[obj["action"]]
        payload["actionNodeRef"] = payload["actionNodeRef"].format(
            uuid=self.context["document"].uuid
        )
        return payload

    def get_contezza_url(self, obj: Union[Document, InformatieObjectDocument]) -> str:
        client = client_from_object(obj)
        url = furl.furl(client.base_url)
        url.path = CONTEZZA_URL_MAPPING[obj["action"]]
        return url.url
