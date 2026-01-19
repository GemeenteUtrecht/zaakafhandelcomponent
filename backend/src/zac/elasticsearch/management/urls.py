from django.urls import path

from .views import IndexElasticsearchView, ReIndexZaakElasticsearchView

urls = [
    path("index", view=IndexElasticsearchView.as_view(), name="index-elasticsearch"),
    path(
        "index/<str:bronorganisatie>/<str:identificatie>",
        ReIndexZaakElasticsearchView.as_view(),
        name="reindex-zaak-elasticsearch",
    ),
]
