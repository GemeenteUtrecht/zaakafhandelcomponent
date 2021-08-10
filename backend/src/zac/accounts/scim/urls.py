from django.urls import include, path

from django_scim.views import GroupSearchView

from zac.accounts.scim.views import GroupsView

urlpatterns = [
    path("Groups", GroupsView.as_view(), name="groups"),
    path("Groups/.search", GroupSearchView.as_view(), name="groups-search"),
    path("Groups/<str:uuid>", GroupsView.as_view(), name="groups-detail"),
    path("", include("django_scim.urls")),
]
