from django.urls import path

from .views import AxesResetView

urls = [path("axes/reset", view=AxesResetView.as_view(), name="axes-reset")]
