from django.urls import path

from .views import FormListView

urlpatterns = [
    path("", FormListView.as_view(), name="form-api-list"),
]
