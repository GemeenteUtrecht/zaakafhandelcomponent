from django.urls import path

from .views import GetZakenView

urlpatterns = [
    path("zaken/autocomplete", GetZakenView.as_view(), name="zaken-search"),
]
