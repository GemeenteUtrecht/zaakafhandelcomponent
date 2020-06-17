from django.urls import include, path

from .views.cache import FlushCacheView
from .views.documents import DownloadDocumentView
from .views.processes import (
    ClaimTaskView,
    FetchMessages,
    FetchTasks,
    PerformTaskView,
    RedirectTaskView,
    RouteTaskView,
    SendMessage,
)
from .views.search import SearchIndexView, SearchView
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
                path(
                    "<bronorganisatie>/<identificatie>/task/<uuid:task_id>/",
                    RouteTaskView.as_view(),
                    name="zaak-task",
                ),
                # task handlers
                path(
                    "<bronorganisatie>/<identificatie>/task/<uuid:task_id>/perform/",
                    PerformTaskView.as_view(),
                    name="perform-task",
                ),
                path(
                    "<bronorganisatie>/<identificatie>/task/<uuid:task_id>/redirect/",
                    RedirectTaskView.as_view(),
                    name="redirect-task",
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
        "search/",
        include(
            [
                path("", SearchIndexView.as_view(), name="search-index"),
                path("_search", SearchView.as_view(), name="search-results"),
            ]
        ),
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
                path("fetch-messages", FetchMessages.as_view(), name="fetch-messages"),
                path("send-message", SendMessage.as_view(), name="send-message"),
                path("flush-cache/", FlushCacheView.as_view(), name="flush-cache"),
            ]
        ),
    ),
]
