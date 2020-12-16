from django_filters import rest_framework as filters
from django_filters.widgets import QueryArrayWidget


class UsernameInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class UserFilter(filters.FilterSet):
    include = UsernameInFilter(field_name="username", widget=QueryArrayWidget)
    exclude = UsernameInFilter(
        field_name="username", widget=QueryArrayWidget, exclude=True
    )
