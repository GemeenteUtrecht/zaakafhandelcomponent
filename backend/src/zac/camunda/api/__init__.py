from django.urls import path

from .views import ProcessInstanceFetchView

urlpatterns = [
    path(
        "fetch-process-instances",
        ProcessInstanceFetchView.as_view(),
        name="fetch-process-instances",
    ),
]
