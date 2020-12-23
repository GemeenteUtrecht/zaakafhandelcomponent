from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularJSONAPIView,
    SpectacularRedocView,
)

urlpatterns = [
    # API schema documentation
    path("", SpectacularJSONAPIView.as_view(schema=None), name="api-schema-json"),
    path("schema", SpectacularAPIView.as_view(schema=None), name="api-schema"),
    path("docs/", SpectacularRedocView.as_view(url_name="api-schema"), name="api-docs"),
    # actual API endpoints
    path("kownsl/", include("zac.contrib.kownsl.urls")),
    path("core/", include("zac.core.api.bff_urls")),
    path("", include("zac.notifications.urls")),
]
