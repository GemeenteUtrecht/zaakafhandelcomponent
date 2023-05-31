from django.urls import path

from .views import IndexAllView

urls = [path("index/all", view=IndexAllView.as_view(), name="index-all")]
