from django.utils.translation import ugettext_lazy as _

from django_filters import rest_framework as filters
from django_filters.widgets import QueryArrayWidget

from ..models import UserAtomicPermission


class StringInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class UserFilterSet(filters.FilterSet):
    include = StringInFilter(
        field_name="username",
        widget=QueryArrayWidget,
        help_text="Deprecated - please use 'include_username' instead.",
    )
    exclude = StringInFilter(
        field_name="username",
        widget=QueryArrayWidget,
        exclude=True,
        help_text="Deprecated - please use 'exclude_username' instead.",
    )
    include_username = StringInFilter(field_name="username", widget=QueryArrayWidget)
    exclude_username = StringInFilter(
        field_name="username", widget=QueryArrayWidget, exclude=True
    )
    include_email = StringInFilter(field_name="email", widget=QueryArrayWidget)
    exclude_email = StringInFilter(
        field_name="email", widget=QueryArrayWidget, exclude=True
    )
    include_groups = StringInFilter(field_name="groups__name", widget=QueryArrayWidget)


class UserAtomicPermissionFilterSet(filters.FilterSet):
    username = filters.CharFilter(
        field_name="user__username",
        help_text=_("Username of user that is filtered on."),
    )
    object_url = filters.CharFilter(
        field_name="atomic_permission__object_url",
        help_text=_("Object URL of object that is filtered on."),
    )

    class Meta:
        model = UserAtomicPermission
        fields = ("username", "object_url")
