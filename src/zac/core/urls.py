from django.urls import path

from .views import (
    DownloadDocumentView,
    FetchZaakObjecten,
    FlushCacheView,
    Index,
    ZaakDetail,
)

app_name = "core"

urlpatterns = [
    path("", Index.as_view(), name="index"),
    path(
        "zaken/<bronorganisatie>/<identificatie>/",
        ZaakDetail.as_view(),
        name="zaak-detail",
    ),
    path(
        "documenten/<bronorganisatie>/<identificatie>/",
        DownloadDocumentView.as_view(),
        name="download-document",
    ),
    path(
        "_fetch-zaakobjecten", FetchZaakObjecten.as_view(), name="fetch-zaakobjecten",
    ),
    path("_flush-cache/", FlushCacheView.as_view(), name="flush-cache"),
]
