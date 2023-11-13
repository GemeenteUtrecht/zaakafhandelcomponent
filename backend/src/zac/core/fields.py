from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from furl import furl
from rest_framework import fields
from zgw_consumers.api_models.documenten import Document

from zac.elasticsearch.documents import InformatieObjectDocument

from .services import get_documenten, get_zaak
from .widgets import AlfrescoDocument


class DownloadDocumentURLField(fields.ReadOnlyField, fields.URLField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label", _("document download URL"))
        kwargs.setdefault(
            "help_text",
            _("The document URL that allows a document to be downloaded."),
        )
        super().__init__(*args, **kwargs)

    def get_attribute(self, instance) -> str:
        assert bool(
            isinstance(instance, Document)
            or isinstance(instance, InformatieObjectDocument),
        ), "This field is only valid for instances of type zgw_consumers.api_models.documenten.Document or zac.elasticsearch.documents.InformatieObjectDocument"
        url = furl(
            reverse(
                "core:download-document",
                kwargs={
                    "bronorganisatie": instance.bronorganisatie,
                    "identificatie": instance.identificatie,
                },
            )
        )
        if instance.versie:
            url.args = {"versie": instance.versie}
        return url.url


class DocWrapper:
    def __init__(self, doc):
        self.doc = doc

    @property
    def download_url(self):
        download_path = reverse(
            "core:download-document",
            kwargs={
                "bronorganisatie": self.doc.bronorganisatie,
                "identificatie": self.doc.identificatie,
            },
        )
        return download_path

    @property
    def icon(self) -> str:
        DEFAULT = "insert_drive_file"
        mimetype = self.doc.formaat

        if not mimetype:
            return DEFAULT

        if mimetype.startswith("image/"):
            return "image"

        if mimetype.startswith("video/"):
            return "ondemand_video"

        if mimetype.startswith("audio/"):
            return "audiotrack"

        return DEFAULT


def get_zaak_documents(zaak_url: str):
    zaak = get_zaak(zaak_url=zaak_url)
    documenten = get_documenten(zaak)
    for doc in documenten:
        yield (doc.url, DocWrapper(doc))


class AlfrescoDocumentField(forms.URLField):
    widget = AlfrescoDocument

    def __init__(self, *, zaak=None, **kwargs):
        super().__init__(**kwargs)
        self.zaak = zaak

    def _get_zaak(self):
        return self._zaak

    def _set_zaak(self, value: str):
        self._zaak = value

    zaak = property(_get_zaak, _set_zaak)
