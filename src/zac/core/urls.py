from django.urls import path

from .views import FlushCacheView, Index

app_name = 'core'

urlpatterns = [
    path('', Index.as_view(), name='index'),
    path('_flush-cache/', FlushCacheView.as_view(), name='flush-cache'),
]
