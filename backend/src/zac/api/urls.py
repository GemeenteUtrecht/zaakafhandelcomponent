from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularJSONAPIView,
    SpectacularRedocView,
)

from .views import health_check, remote_schema_view

urlpatterns = [
    # API schema documentation
    path("", SpectacularJSONAPIView.as_view(schema=None), name="api-schema-json"),
    path("_health/", health_check, name="health-check"),
    path("_get-remote-schema/", remote_schema_view, name="get-remote-schema"),
    path("schema", SpectacularAPIView.as_view(schema=None), name="api-schema"),
    path(
        "docs/",
        SpectacularRedocView.as_view(url_name="api-schema-json"),
        name="api-docs",
    ),
    # actual API endpoints
    path("accounts/", include("zac.accounts.api.urls")),
    path("activities/", include("zac.activities.api.urls")),
    path("camunda/", include("zac.camunda.api.urls")),
    path("checklists/", include("zac.checklists.api.urls")),
    path("core/", include("zac.core.api.bff_urls")),
    path("dashboard/", include("zac.contrib.board.api.urls")),
    path("dowc/", include("zac.contrib.dowc.urls")),
    path("forms/", include("zac.forms.api.urls")),
    path("kadaster/", include("zac.contrib.kadaster.urls")),
    path("kownsl/", include("zac.contrib.kownsl.urls")),
    path("search/", include("zac.elasticsearch.drf_api.urls")),
    path("workstack/", include("zac.werkvoorraad.api.urls")),
    path("", include("zac.notifications.urls")),
]
