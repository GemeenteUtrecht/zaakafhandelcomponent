from typing import List, Optional

from django.urls import reverse
from django.utils.translation import gettext as _

from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from .constants import DocFileTypes
from .data import DowcResponse


class DowcResponseSerializer(APIModelSerializer):
    delete_url = serializers.SerializerMethodField(
        label=_("deletion url"),
        help_text=_(
            "A DELETE request to this URL will update, if necessary, and delete the resource."
        ),
    )

    class Meta:
        model = DowcResponse
        fields = (
            "purpose",
            "magic_url",
            "delete_url",
        )
        extra_kwargs = {
            "purpose": {
                "read_only": True,
            },
            "magic_url": {
                "read_only": True,
            },
        }

    def get_delete_url(self, obj) -> str:
        if obj.purpose == DocFileTypes.write:
            return reverse(
                "dowc:patch-destroy-doc", kwargs={"dowc_request_uuid": obj.uuid}
            )
        else:
            return ""


class DowcSerializer(APIModelSerializer):
    class Meta:
        model = DowcResponse
        fields = "uuid"
