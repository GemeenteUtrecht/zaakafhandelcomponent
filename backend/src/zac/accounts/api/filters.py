from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as filters
from django_filters.widgets import QueryArrayWidget

from ..models import UserAtomicPermission, UserAuthorizationProfile


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
        required=True,
    )
    object_url = filters.CharFilter(
        field_name="atomic_permission__object_url",
        help_text=_("Object URL of object that is filtered on."),
        required=True,
    )

    class Meta:
        model = UserAtomicPermission
        fields = ("username", "object_url")

    def is_valid(self):
        valid_fields = list(self.get_fields().keys())
        any_valid_fields = {
            param: val for param, val in self.data.items() if param in valid_fields
        }
        for field, val in any_valid_fields.items():
            if not val or not all(val):
                self.form.add_error(
                    None,
                    ValidationError(
                        _(
                            "Please include a valid non-empty string for {field}."
                        ).format(field=field),
                        code="query-param-non-empty",
                    ),
                )
        return super().is_valid()


class UserAuthorizationProfileFilterSet(filters.FilterSet):
    username = filters.CharFilter(
        field_name="user__username",
        help_text=_("Username of user that is filtered on. Cannot be empty if given."),
    )
    auth_profile = filters.CharFilter(
        field_name="auth_profile__uuid",
        help_text=_(
            "`uuid` of authorization profile that is filtered on. Cannot be empty if given."
        ),
    )
    is_active = filters.BooleanFilter(
        help_text=_("Filter based on active profiles."),
    )

    class Meta:
        model = UserAuthorizationProfile
        fields = ("username", "auth_profile", "is_active")

    def is_valid(self):
        valid_fields = list(self.get_fields().keys())
        any_valid_fields = {
            param: val for param, val in self.data.items() if param in valid_fields
        }
        if not any_valid_fields:
            self.form.add_error(
                None,
                ValidationError(
                    _(
                        "Please include one of the following query parameters: {query_param}"
                    ).format(query_param=list(self.get_fields().keys())),
                    code="query-param-not-set",
                ),
            )
        for field, val in any_valid_fields.items():
            if not val or not all(val):
                self.form.add_error(
                    None,
                    ValidationError(
                        _(
                            "Please include a valid non-empty string for {field}."
                        ).format(field=field),
                        code="query-param-non-empty",
                    ),
                )
        return super().is_valid()
