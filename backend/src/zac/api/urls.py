from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularJSONAPIView,
    SpectacularRedocView,
)

urlpatterns = [
    path("", SpectacularAPIView.as_view(), name="api-schema-json"),
    path("schema", SpectacularJSONAPIView.as_view(), name="api-schema"),
    path("docs/", SpectacularRedocView.as_view(url_name="api-schema"), name="api-docs"),
]
