from django.urls import include, path

from . import api

app_name = "camunda"

urlpatterns = [path("api/camunda/", include(api))]
