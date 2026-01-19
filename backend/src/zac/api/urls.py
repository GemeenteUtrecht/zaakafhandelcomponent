from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularJSONAPIView,
    SpectacularRedocView,
)

from .views import HealthCheckView, PingView, remote_schema_view

urlpatterns = [
    # API schema documentation
    path("", SpectacularJSONAPIView.as_view(schema=None), name="api-schema-json"),
    path("_health/", HealthCheckView.as_view(), name="health-check"),
    path("ping/", PingView.as_view(), name="ping"),
    path("_get-remote-schema", remote_schema_view, name="get-remote-schema"),
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
    path("checklists/", include("zac.contrib.objects.checklists.api.urls")),
    path("core/", include("zac.core.api.bff_urls")),
    path("dashboard/", include("zac.contrib.board.api.urls")),
    path("dowc/", include("zac.contrib.dowc.urls")),
    path("forms/", include("zac.forms.api.urls")),
    path("kadaster/", include("zac.contrib.kadaster.urls")),
    path("kownsl/", include("zac.contrib.objects.kownsl.api.urls")),
    path("landing-page/", include("zac.landing.api.urls")),
    path("oudbehandelaren/", include("zac.contrib.objects.oudbehandelaren.api.urls")),
    path("search/", include("zac.elasticsearch.drf_api.urls")),
    path("workstack/", include("zac.werkvoorraad.urls")),
    path("", include("zac.notifications.urls")),
]
