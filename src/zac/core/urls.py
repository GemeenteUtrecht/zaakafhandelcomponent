from django.urls import include, path

from .views.cache import FlushCacheView
from .views.documents import DownloadDocumentView
from .views.processes import ClaimTaskView, FetchTasks
from .views.search import SearchIndexView
from .views.zaken import FetchZaakObjecten, Index, ZaakAfhandelView, ZaakDetail

app_name = "core"

urlpatterns = [
    path(
        "zaken/",
        include(
            [
                path("", Index.as_view(), name="index"),
                path(
                    "<bronorganisatie>/<identificatie>/",
                    ZaakDetail.as_view(),
                    name="zaak-detail",
                ),
                path(
                    "<bronorganisatie>/<identificatie>/afhandelen/",
                    ZaakAfhandelView.as_view(),
                    name="zaak-afhandeling",
                ),
            ]
        ),
    ),
    path(
        "documenten/",
        include(
            [
                path(
                    "<bronorganisatie>/<identificatie>/",
                    DownloadDocumentView.as_view(),
                    name="download-document",
                ),
            ]
        ),
    ),
    path(
        "search/", include([path("", SearchIndexView.as_view(), name="search-index"),])
    ),
    path(
        "_",
        include(
            [
                path(
                    "fetch-zaakobjecten",
                    FetchZaakObjecten.as_view(),
                    name="fetch-zaakobjecten",
                ),
                path("fetch-tasks", FetchTasks.as_view(), name="fetch-tasks"),
                path("claim-task", ClaimTaskView.as_view(), name="claim-task"),
                path("flush-cache/", FlushCacheView.as_view(), name="flush-cache"),
            ]
        ),
    ),
]
