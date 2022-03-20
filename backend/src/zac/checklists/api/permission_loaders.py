from typing import List

from zac.accounts.constants import PermissionReason
from zac.accounts.models import User, UserAtomicPermission
from zac.accounts.permission_loaders import add_atomic_permission_to_user
from zac.core.permissions import zaken_inzien

from ..models import Checklist
from ..permissions import checklists_inzien, checklists_schrijven


def add_permissions_for_checklist_assignee(
    checklist: Checklist, user: User
) -> List[UserAtomicPermission]:
    user_atomic_permissions = []
    for permission in [zaken_inzien, checklists_inzien, checklists_schrijven]:
        user_atomic_permission = add_atomic_permission_to_user(
            user,
            checklist.zaak,
            permission_name=permission.name,
            reason=PermissionReason.checklist,
        )
        if user_atomic_permission:
            user_atomic_permissions.append(user_atomic_permission)
    return user_atomic_permissions
