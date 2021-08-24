from django.contrib.auth.decorators import permission_required
from django.urls import include, path

from decorator_include import decorator_include
from django_scim.views import GroupSearchView

from zac.accounts.scim.views import GroupsView

scim_use_required = permission_required("accounts.use_scim", raise_exception=True)

urlpatterns = [
    path(
        "",
        decorator_include(
            scim_use_required,
            [
                path("Groups", GroupsView.as_view(), name="groups"),
                path("Groups/.search", GroupSearchView.as_view(), name="groups-search"),
                path("Groups/<str:uuid>", GroupsView.as_view(), name="groups-detail"),
                path("", include("django_scim.urls")),
            ],
        ),
    )
]
