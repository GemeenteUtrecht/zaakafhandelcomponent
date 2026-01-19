from drf_spectacular.extensions import OpenApiSerializerExtension
from drf_spectacular.plumbing import ResolvedComponent

from ..proxy import ProxySerializer
from ..utils import remote_schema_ref


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
        ref = remote_schema_ref(base, serializer.PROXY_SCHEMA_PATH)

        # get the extra serializer
        extra = ResolvedComponent(
            name=f"{base_name}Extras{direction.capitalize()}",
            type=ResolvedComponent.SCHEMA,
            schema=auto_schema._map_basic_serializer(serializer, direction),
            object=serializer,
        )
        auto_schema.registry.register(extra)
        return {
            "allOf": [ref, extra.ref],
        }
