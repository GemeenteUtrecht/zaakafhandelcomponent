from django.urls import path

from .views import SelectFormView

app_name = "forms"

urlpatterns = [
    path("", SelectFormView.as_view(), name="select-form"),
]
