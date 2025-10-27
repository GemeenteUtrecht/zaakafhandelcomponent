from django.conf import settings
from django.utils.translation import gettext_lazy as _

from drf_spectacular.openapi import AutoSchema as _AutoSchema
from drf_spectacular.plumbing import build_media_type_object, force_instance
from drf_spectacular.utils import OpenApiParameter

# ensure extensions are loaded
from .drf_spectacular import polymorphic  # noqa
from .drf_spectacular import proxy  # noqa


class AutoSchema(_AutoSchema):
    def _get_request_body(self):
        serializer = force_instance(self.get_request_serializer())

        if isinstance(serializer, dict):
            # mapping of content-type to schema
            request_body = {
                "content": {
                    media_type: build_media_type_object(
                        serializer[media_type],
                        self._get_examples(
                            serializer[media_type], "request", media_type
                        ),
                    )
                    for media_type in self.map_parsers()
                    if media_type in serializer
                }
            }
            return request_body

        return super()._get_request_body()

    def get_summary(self):
        action_or_method = getattr(
            self.view, getattr(self.view, "action", self.method.lower()), None
        )
        cls_summary = getattr(self.view.__class__, "schema_summary", None)
        action_or_method_summary = getattr(action_or_method, "schema_summary", None)
        return action_or_method_summary or cls_summary

    def get_override_parameters(self):
        """Add hijack header"""
        hijack_response_header = OpenApiParameter(
            name=settings.HIJACK_HEADER,
            type=str,
            location=OpenApiParameter.HEADER,
            description=_("Header displays if the user is hijacked."),
            enum=["false", "true"],
            response=True,
        )

        return [hijack_response_header]
