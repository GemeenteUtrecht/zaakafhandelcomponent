from typing import List

from zac.accounts.constants import PermissionReason
from zac.accounts.models import UserAtomicPermission
from zac.accounts.permission_loaders import add_atomic_permission_to_user
from zac.core.permissions import zaken_inzien

from ..models import Activity
from ..permissions import activiteiten_schrijven, activities_read


def add_permissions_for_activity_assignee(
    activity: Activity,
) -> List[UserAtomicPermission]:
    user_atomic_permissions = []
    for permission in [zaken_inzien, activities_read, activiteiten_schrijven]:
        user_atomic_permission = add_atomic_permission_to_user(
            activity.assignee,
            activity.zaak,
            permission_name=permission.name,
            reason=PermissionReason.activiteit,
        )
        if user_atomic_permission:
            user_atomic_permissions.append(user_atomic_permission)
    return user_atomic_permissions
