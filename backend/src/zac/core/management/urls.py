from django.urls import path

from .views import CacheResetView

urls = [path("cache/reset", view=CacheResetView.as_view(), name="cache-reset")]
