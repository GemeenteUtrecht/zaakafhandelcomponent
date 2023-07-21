from django.urls import path

from .views import UnlockChecklistsView

urls = [
    path(
        "checklists/unlock",
        view=UnlockChecklistsView.as_view(),
        name="unlock-checklists",
    ),
]
