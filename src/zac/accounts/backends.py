from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password

import rules

from zac.utils.decorators import cache

from .datastructures import ZaakPermissionCollection


class UserModelEmailBackend(ModelBackend):
    """
    Authentication backend for login with email address.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = get_user_model().objects.get(email__iexact=username, is_active=True)
            if check_password(password, user.password):
                return user
        except get_user_model().DoesNotExist:
            # No user was found, return None - triggers default login failed
            return None


# TODO: invalidate cache on permission changes!
@cache("user:permission-codes:{user.id}", timeout=60 * 5)
def _get_user_permission_codes(user):
    # inventory of non-object level permissions
    qs = user.auth_profiles.values_list("permission_sets__permissions", flat=True)
    return set(sum(qs, []))


class PermissionsBackend:
    def authenticate(self, request):
        return None

    def set_user_permissions(self, user):
        """
        Fetch the (zaaktype) permissions for the user and cache them…
        """
        if not hasattr(user, "_zaaktype_perms"):
            user._zaaktype_perms = ZaakPermissionCollection.for_user(user)
        return user._zaaktype_perms

    def has_perm(self, user_obj, perm: str, obj=None) -> bool:
        if not user_obj.is_active:
            return False

        self.set_user_permissions(user_obj)

        # inventory of non-object level permissions
        permission_codes = _get_user_permission_codes(user_obj)
        if not obj and perm not in permission_codes:
            if not rules.rule_exists(perm):
                return False
            return rules.test_rule(perm, user_obj)

        # "does the user have the permission at all?" -> yes
        if not obj:
            return True

        # defer object-level permission checks to the rules setup
        return rules.test_rule(perm, user_obj, obj)
