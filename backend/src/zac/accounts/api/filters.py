from django_filters import rest_framework as filters
from django_filters.widgets import QueryArrayWidget


class StringInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class UserFilter(filters.FilterSet):
    include_username = StringInFilter(field_name="username", widget=QueryArrayWidget)
    exclude_username = StringInFilter(
        field_name="username", widget=QueryArrayWidget, exclude=True
    )
    include_email = StringInFilter(field_name="email", widget=QueryArrayWidget)
    exclude_email = StringInFilter(
        field_name="email", widget=QueryArrayWidget, exclude=True
    )
