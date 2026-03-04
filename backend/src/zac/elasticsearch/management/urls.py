from django.urls import path

from .views import FixVAOrderView, IndexElasticsearchView, ReIndexZaakElasticsearchView

urls = [
    path("index", view=IndexElasticsearchView.as_view(), name="index-elasticsearch"),
    path(
        "index/<str:bronorganisatie>/<str:identificatie>",
        ReIndexZaakElasticsearchView.as_view(),
        name="reindex-zaak-elasticsearch",
    ),
    path(
        "fix-va-order", view=FixVAOrderView.as_view(), name="fix-va-order-elasticsearch"
    ),
]
