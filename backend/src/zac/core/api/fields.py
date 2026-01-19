from typing import Dict, Type

from django.utils.translation import gettext_lazy as _

from rest_framework import fields, relations
from rest_framework.serializers import Serializer

from .validators import ZaakDocumentsValidator


class SerializerSlugRelatedField(relations.SlugRelatedField):
    response_serializer = None

    def get_response_serializer(self, obj: object) -> Type[Serializer]:
        assert self.response_serializer
        return self.response_serializer(obj)

    def to_representation(self, obj) -> Dict:
        if self.allow_null and not obj:
            return dict()

        return self.get_response_serializer(obj).data


class SelectDocumentsCamundaField(fields.ListField):
    """
    Specialized field for camunda tasks where document selection takes place.
    Requires a `get_zaak_from_context` method on the serializer.

    """

    child = fields.URLField()

    default_validators = [
        ZaakDocumentsValidator(),
    ]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label", _("Select the relevant documents for Camunda task."))
        kwargs.setdefault(
            "help_text",
            _(
                "These are the documents that belong to the ZAAK. Please select relevant documents."
            ),
        )
        super().__init__(*args, **kwargs)


class NullableJsonField(fields.JSONField):
    def get_attribute(self, instance):
        """
        Skip field if it's not included in the request.
        Nested fields are not supported
        """

        try:  # check if instance is iterable
            iter(instance)
        except TypeError:
            raise fields.SkipField()

        if self.source not in instance:
            raise fields.SkipField()

        return super().get_attribute(instance)
