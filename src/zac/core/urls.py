from django.urls import path

from .views import FlushCacheView, Index, ZaakDetail

app_name = 'core'

urlpatterns = [
    path('', Index.as_view(), name='index'),
    path('<bronorganisatie>/<identificatie>/', ZaakDetail.as_view(), name='zaak-detail'),
    path('_flush-cache/', FlushCacheView.as_view(), name='flush-cache'),
]
