from django.urls import path

from .views.cache import FlushCacheView
from .views.documents import DownloadDocumentView
from .views.processes import ClaimTaskView, FetchTasks
from .views.zaken import FetchZaakObjecten, Index, ZaakAfhandelView, ZaakDetail

app_name = "core"

urlpatterns = [
    path("", Index.as_view(), name="index"),
    path(
        "zaken/<bronorganisatie>/<identificatie>/",
        ZaakDetail.as_view(),
        name="zaak-detail",
    ),
    path(
        "zaken/<bronorganisatie>/<identificatie>/afhandelen/",
        ZaakAfhandelView.as_view(),
        name="zaak-afhandeling",
    ),
    path(
        "documenten/<bronorganisatie>/<identificatie>/",
        DownloadDocumentView.as_view(),
        name="download-document",
    ),
    path(
        "_fetch-zaakobjecten", FetchZaakObjecten.as_view(), name="fetch-zaakobjecten",
    ),
    path("_fetch-tasks", FetchTasks.as_view(), name="fetch-tasks"),
    path("_claim-task", ClaimTaskView.as_view(), name="claim-task"),
    path("_flush-cache/", FlushCacheView.as_view(), name="flush-cache"),
]
