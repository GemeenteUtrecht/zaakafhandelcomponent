from drf_spectacular.openapi import AutoSchema as _AutoSchema
from drf_spectacular.plumbing import build_media_type_object, force_instance


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
