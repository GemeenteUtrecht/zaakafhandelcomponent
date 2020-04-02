from django.urls import include, path

from . import api

app_name = "kadaster"

urlpatterns = [path("api/kadaster/", include(api))]
