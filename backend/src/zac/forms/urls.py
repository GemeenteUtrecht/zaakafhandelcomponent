from django.urls import path

from .views import RenderFormView, SelectFormView

app_name = "forms"

urlpatterns = [
    path("", SelectFormView.as_view(), name="select-form"),
    path("<int:form_id>/", RenderFormView.as_view(), name="render-form"),
]
