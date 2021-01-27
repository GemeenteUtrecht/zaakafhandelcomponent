from django.urls import include, path

from .views import DeleteDowcView, OpenDowcView

app_name = "dowc"

urlpatterns = [
    path(
        "<uuid:dowc_request_uuid>/",
        DeleteDowcView.as_view(),
        name="patch-destroy-doc",
    ),
    path(
        "<str:bronorganisatie>/<str:identificatie>/<str:purpose>",
        OpenDowcView.as_view(),
        name="request-doc",
    ),
]
