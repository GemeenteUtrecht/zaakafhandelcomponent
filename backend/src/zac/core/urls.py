from django.urls import include, path

from .views.besluiten import BesluitCreateView, ZaakBesluitenView
from .views.documents import DownloadDocumentView

app_name = "core"

urlpatterns = [
    path("api/", include("zac.core.api.urls")),
    path(
        "zaken/",  # TODO: REFACTOR TO NEW FRONTEND
        include(
            [
                path(
                    "<bronorganisatie>/<identificatie>/besluiten/",
                    ZaakBesluitenView.as_view(),
                    name="zaak-besluiten",
                ),
                path(
                    "<bronorganisatie>/<identificatie>/besluiten/nieuw/",
                    BesluitCreateView.as_view(),
                    name="add-besluit",
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
]
