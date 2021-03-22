from django.utils.translation import gettext_lazy as _

from rest_framework import fields
from zgw_consumers.api_models.documenten import Document

from .constants import DocFileTypes
from .utils import get_dowc_url


class DowcUrlFieldReadOnly(fields.ReadOnlyField, fields.URLField):
    def __init__(self, *args, purpose: str = DocFileTypes.read, **kwargs):
        self.purpose = purpose
        kwargs.setdefault("label", _("document {purpose} URL").format(purpose=purpose))
        kwargs.setdefault(
            "help_text",
            _(
                "The document {purpose} URL that allows a document to be opened by the MS Office WebDAV client."
            ).format(purpose=purpose),
        )
        super().__init__(*args, **kwargs)

    def get_attribute(self, instance):
        assert isinstance(
            instance, Document
        ), "This field is only valid for instances of type zgw_consumers.api_models.documenten.Document"
        return get_dowc_url(instance, self.purpose)
