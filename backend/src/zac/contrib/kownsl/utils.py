"""
API documentation utils.

The internal API proxies to Kownsl, so we also point the API schema references to the
Kownsl API spec.

The Kownsl API spec inlines everything - it doesn't yet make use of components. For that
reason, we currently need to hardcode the URLs rather than relying on operation IDs,
for example. In the future, we'll be able to point to
``#/components/schemas/ReviewRequest`` for example.
"""
from django.conf import settings

from drf_spectacular.utils import extend_schema

from zac.api.utils import remote_schema_ref


def remote_kownsl_create_schema(
    url: str, status_code=201, media_type="application/json", **kwargs
) -> callable:
    """
    Extend the schema to include request and response bodies from a remote schema.
    """
    method_path = ["paths", url, "post"]
    schema_path = ["content", media_type, "schema"]
    request_schema = [*method_path, "requestBody", *schema_path]
    response_schema = [*method_path, "responses", "201", *schema_path]
    return extend_schema(
        request={
            media_type: remote_schema_ref(
                settings.EXTERNAL_API_SCHEMAS["KOWNSL_API_SCHEMA"], request_schema
            ),
        },
        responses={
            (status_code, media_type): remote_schema_ref(
                settings.EXTERNAL_API_SCHEMAS["KOWNSL_API_SCHEMA"], response_schema
            ),
        },
        **kwargs,
    )
