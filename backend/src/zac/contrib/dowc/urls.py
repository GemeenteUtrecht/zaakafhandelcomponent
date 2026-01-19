from django.urls import path

from .views import DeleteDowcView, OpenDowcView

app_name = "dowc"

urlpatterns = [
    path(
        "<uuid:dowc_uuid>/",
        DeleteDowcView.as_view(),
        name="patch-destroy-doc",
    ),
    path(
        "<str:bronorganisatie>/<str:identificatie>/<str:purpose>",
        OpenDowcView.as_view(),
        name="request-doc",
    ),
]
