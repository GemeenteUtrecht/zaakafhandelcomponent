from typing import List, Optional

from django.urls import reverse
from django.utils.translation import gettext as _

from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.contrib.documents.data import DocRequest


class DocRequestSerializer(APIModelSerializer):
    delete_url = serializers.SerializerMethodField(
        label=_("deletion url"),
        help_text=_(
            "A DELETE request to this URL will update, if necessary, and delete the resource."
        ),
    )

    class Meta:
        model = DocRequest
        fields = (
            "uuid",
            "purpose",
            "drc_url",
        )

    def get_delete_url(self, obj) -> str:
        return reverse("doc:delete-document", kwargs={"doc_request_uuid": obj.uuid})
