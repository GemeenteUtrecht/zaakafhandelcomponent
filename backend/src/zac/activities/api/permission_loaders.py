from typing import List

from zac.accounts.constants import PermissionReason
from zac.accounts.models import AtomicPermission
from zac.accounts.permission_loaders import add_atomic_permission_to_user

from ..models import Activity
from ..permissions import activiteiten_schrijven, activities_read


def add_permissions_for_activity_assignee(activity: Activity) -> List[AtomicPermission]:
    atomic_permissions = []
    for permission in [activities_read, activiteiten_schrijven]:
        atomic_permission = add_atomic_permission_to_user(
            activity.assignee,
            activity.zaak,
            permission_name=permission.name,
            reason=PermissionReason.activiteit,
        )
        if atomic_permission:
            atomic_permissions.append(atomic_permission)
    return atomic_permissions
