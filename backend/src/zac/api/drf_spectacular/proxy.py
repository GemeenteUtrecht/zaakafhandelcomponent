from drf_spectacular.extensions import OpenApiSerializerExtension
from drf_spectacular.plumbing import ResolvedComponent

from ..proxy import ProxySerializer
from ..utils import remote_schema_ref


def get_remote_schema_ref(
    base: str, url: str, status_code=200, media_type="application/json"
):
    response_schema = [
        "paths",
        url,
        "get",
        "responses",
        status_code,
        "content",
        media_type,
        "schema",
    ]
    return remote_schema_ref(base, response_schema)


class ProxySerializerExtension(OpenApiSerializerExtension):
    target_class = ProxySerializer
    match_subclasses = True

    def _get_name_base(self) -> str:
        serializer = self.target
        name = serializer.__class__.__name__
        if name.endswith("Serializer"):
            name = name[:-10]
        return name

    def map_serializer(self, auto_schema, direction):
        serializer = self.target
        base_name = self._get_name_base()

        base = serializer.PROXY_SCHEMA_BASE
        path, method = serializer.PROXY_SCHEMA
        ref = get_remote_schema_ref(base, path)

        # get the extra serializer
        extra = ResolvedComponent(
            name=f"{base_name}Extras",
            type=ResolvedComponent.SCHEMA,
            schema=auto_schema._map_basic_serializer(serializer, direction),
            object=serializer,
        )
        auto_schema.registry.register(extra)
        return {
            "allOf": [ref, extra.ref],
        }
