from django.urls import include, path

from . import api

app_name = "activities"

urlpatterns = [
    path("api/", include(api)),
]
