from django.urls import reverse
from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework_dataclasses.serializers import DataclassSerializer

from .constants import DocFileTypes
from .data import DowcResponse


class DowcResponseSerializer(DataclassSerializer):
    delete_url = serializers.SerializerMethodField(
        label=_("deletion url"),
        help_text=_(
            "A DELETE request to this URL will update, if necessary, and delete the resource."
        ),
    )

    class Meta:
        dataclass = DowcResponse
        fields = (
            "drc_url",
            "purpose",
            "magic_url",
            "delete_url",
            "unversioned_url",
        )
        extra_kwargs = {
            "purpose": {
                "read_only": True,
            },
            "magic_url": {
                "read_only": True,
            },
            "unversioned_url": {
                "read_only": True,
            },
        }

    def get_delete_url(self, obj) -> str:
        return (
            reverse("dowc:patch-destroy-doc", kwargs={"dowc_uuid": obj.uuid})
            if obj.purpose == DocFileTypes.write
            else ""
        )


class DeleteDowcSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(help_text=_("UUID of DoWC object."), required=True)


class DowcSerializer(serializers.Serializer):
    zaak = serializers.URLField(
        help_text=_("URL-reference to ZAAK."), required=False, allow_blank=True
    )
