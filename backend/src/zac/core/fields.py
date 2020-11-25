from django import forms
from django.urls import reverse

from .services import get_documenten, get_zaak
from .widgets import AlfrescoDocument, DocumentSelectMultiple


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
    documenten, _ = get_documenten(zaak)
    for doc in documenten:
        yield (doc.url, DocWrapper(doc))


class DocumentsMultipleChoiceField(forms.MultipleChoiceField):
    widget = DocumentSelectMultiple

    def __init__(self, *, zaak=None, **kwargs):
        super().__init__(**kwargs)
        self.zaak = zaak

    def _get_zaak(self):
        return self._zaak

    def _set_zaak(self, value: str):
        self._zaak = value
        if self._zaak:
            self.choices = lambda: get_zaak_documents(self._zaak)

    zaak = property(_get_zaak, _set_zaak)


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
