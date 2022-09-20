from typing import List
from urllib.request import Request

from zac.accounts.models import BlueprintPermission, Role, UserAtomicPermission
from zac.accounts.permissions import Permission

from .permissions import registry


def permissions_related_to_user(request: Request) -> List[Permission]:
    """
    Returns permissions that a user has.

    """
    # superuser has all perms
    all_perms = sorted(list(registry.values()), key=lambda perm: perm.name.split(":"))
    if request.user.is_superuser:
        return all_perms

    all_perms = sorted(list(registry.values()), key=lambda perm: perm.name.split(":"))

    # first grab permissions related to atomic permissions for user
    user_atomic_perms = set(
        UserAtomicPermission.objects.select_related("atomic_permission")
        .filter(user=request.user)
        .values_list("atomic_permission__permission", flat=True)
    )

    # then grab permissions related to roles related to blueprint permissions the user has
    role_perms = Role.objects.filter(
        blueprint_permissions__in=BlueprintPermission.objects.for_requester(request)
    ).values_list("permissions", flat=True)
    user_role_perms = {perm for perms in role_perms for perm in perms}

    # finally filter out all those that are allowed
    allowed_perms = [
        perm
        for perm in all_perms
        if perm.name in user_atomic_perms.union(user_role_perms)
    ]
    return allowed_perms
