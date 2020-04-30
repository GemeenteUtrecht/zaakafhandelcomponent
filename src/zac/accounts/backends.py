from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password

from .permissions import Permission, registry


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


class PermissionsBackend:
    def has_perm(self, user_obj, perm: str, obj=None) -> bool:
        if not user_obj.is_active:
            return False

        if obj:
            import bpdb

            bpdb.set_trace()

        # inventory of non-object level permissions
        qs = user_obj.auth_profiles.values_list(
            "permission_sets__permissions", flat=True
        )
        permission_codes = set(sum(qs, []))
        return perm in permission_codes
