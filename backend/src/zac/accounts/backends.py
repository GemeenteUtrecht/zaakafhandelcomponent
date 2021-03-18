from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password

from zac.accounts.constants import PermissionObjectType
from zac.accounts.models import PermissionDefinition


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


# Deprecated
# this class is used only to support legacy SSR views
# All DRF views should use zac.api.permissions.DefinitionBasePermission and its subclasses
class PermissionsBackend:
    def authenticate(self, request):
        return None

    def has_perm(
        self,
        user_obj,
        perm: str,
        obj=None,
        object_type=PermissionObjectType.zaak,
        request=None,
    ) -> bool:
        if not user_obj.is_active:
            return False

        user_permissions = (
            PermissionDefinition.objects.for_user(user_obj)
            .filter(permission=perm, object_type=object_type)
            .actual()
        )

        # similar to DefinitionBasePermission.has_permission
        if not obj:
            return user_permissions.exists()

        # similar to DefinitionBasePermission.has_object_permission
        if user_permissions.filter(object_url=obj.url).exists():
            return True

        for permission in user_permissions.filter(object_url=""):
            if permission.has_policy_access(obj, user=user_obj):
                return True

        return False
