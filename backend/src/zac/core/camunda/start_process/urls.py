from django.urls import path

from .views import StartCamundaProcessView

urlpatterns = [
    path("start-process", StartCamundaProcessView.as_view(), name="start-process")
]
