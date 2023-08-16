from django.urls import path

from .views import (
    AddAtomicPermissionsView,
    AxesResetView,
    ClearRecentlyViewedView,
    LoadBlueprintPermissionsView,
)

urls = [
    path("axes/reset", view=AxesResetView.as_view(), name="axes-reset"),
    path(
        "permissions/blueprint/load",
        view=LoadBlueprintPermissionsView.as_view(),
        name="load-blueprint-permissions",
    ),
    path(
        "permissions/atomic/add",
        view=AddAtomicPermissionsView.as_view(),
        name="add-atomic-permissions",
    ),
    path(
        "user/recently-viewed/clear",
        ClearRecentlyViewedView.as_view(),
        name="recently-viewed-clear",
    ),
]
