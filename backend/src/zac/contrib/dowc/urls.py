from django.urls import include, path

from .views import DowcView

app_name = "dowc"

urlpatterns = [
    path(
        "<uuid:dowc_request_uuid>/",
        DowcView.as_view(),
        name="patch-destroy-doc",
    ),
    path(
        "<str:bronorganisatie>/<str:identificatie>/<str:purpose>",
        DowcView.as_view(),
        name="request-doc",
    ),
]
