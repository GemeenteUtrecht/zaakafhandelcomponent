from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularJSONAPIView,
    SpectacularRedocView,
)

from .views import remote_schema_view

urlpatterns = [
    # API schema documentation
    path("", SpectacularJSONAPIView.as_view(schema=None), name="api-schema-json"),
    path("_get-remote-schema/", remote_schema_view, name="get-remote-schema"),
    path("schema", SpectacularAPIView.as_view(schema=None), name="api-schema"),
    path("docs/", SpectacularRedocView.as_view(url_name="api-schema"), name="api-docs"),
    # actual API endpoints
    path("accounts/", include("zac.accounts.api.urls")),
    path("kownsl/", include("zac.contrib.kownsl.urls")),
    path("dowc/", include("zac.contrib.dowc.urls")),
    path("core/", include("zac.core.api.bff_urls")),
    path("camunda/", include("zac.camunda.api.urls")),
    path("search/", include("zac.elasticsearch.drf_api.urls")),
    path("workstack/", include("zac.werkvoorraad.urls")),
    path("", include("zac.notifications.urls")),
]
