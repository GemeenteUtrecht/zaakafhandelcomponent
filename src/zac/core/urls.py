from django.urls import include, path

from .views.besluiten import ZaakBesluitenView
from .views.cache import FlushCacheView
from .views.documents import DownloadDocumentView
from .views.processes import (
    ClaimTaskView,
    PerformTaskView,
    RedirectTaskView,
    RouteTaskView,
    SendMessage,
)
from .views.search import SearchIndexView, SearchView
from .views.zaken import (
    AccessRequestCreateView,
    FetchZaakObjecten,
    Index,
    ZaakAccessRequestsView,
    ZaakActiviteitenView,
    ZaakAfhandelView,
    ZaakDetail,
)

app_name = "core"

urlpatterns = [
    path("api/", include("zac.core.api.urls")),
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
                    "<bronorganisatie>/<identificatie>/activiteiten/",
                    ZaakActiviteitenView.as_view(),
                    name="zaak-activiteiten",
                ),
                path(
                    "<bronorganisatie>/<identificatie>/besluiten/",
                    ZaakBesluitenView.as_view(),
                    name="zaak-besluiten",
                ),
                path(
                    "<bronorganisatie>/<identificatie>/afhandelen/",
                    ZaakAfhandelView.as_view(),
                    name="zaak-afhandeling",
                ),
                path(
                    "<bronorganisatie>/<identificatie>/access-requests/add/",
                    AccessRequestCreateView.as_view(),
                    name="access-request-create",
                ),
                path(
                    "<bronorganisatie>/<identificatie>/access-requests/",
                    ZaakAccessRequestsView.as_view(),
                    name="zaak-access-requests",
                ),
            ]
        ),
    ),
    path(
        "user-tasks/",
        include(
            [
                path(
                    "<uuid:task_id>/",
                    RouteTaskView.as_view(),
                    name="zaak-task",
                ),
                # task handlers
                path(
                    "<uuid:task_id>/perform/",
                    PerformTaskView.as_view(),
                    name="perform-task",
                ),
                path(
                    "<uuid:task_id>/redirect/",
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
                path("claim-task", ClaimTaskView.as_view(), name="claim-task"),
                path("send-message", SendMessage.as_view(), name="send-message"),
                path("flush-cache/", FlushCacheView.as_view(), name="flush-cache"),
            ]
        ),
    ),
]
