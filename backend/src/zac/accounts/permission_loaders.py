from typing import List, Optional, Union

from zac.contrib.kownsl.data import KownslTypes, ReviewRequest
from zac.core.permissions import zaken_inzien
from zac.core.rollen import Rol
from zac.core.services import fetch_rol
from zgw.models.zrc import Zaak

from .constants import PermissionObjectType, PermissionReason
from .models import AtomicPermission, User, UserAtomicPermission


def add_atomic_permission_to_user(
    user: User,
    object_url: str,
    object_type: str = PermissionObjectType.zaak,
    permission_name: str = zaken_inzien.name,
    reason: str = "",
) -> Optional[UserAtomicPermission]:
    if (
        UserAtomicPermission.objects.select_related("atomic_permission")
        .filter(
            user=user,
            atomic_permission__object_type=object_type,
            atomic_permission__object_url=object_url,
            atomic_permission__permission=permission_name,
        )
        .actual()
        .exists()
    ):
        return None

    atomic_permission, created = AtomicPermission.objects.get_or_create(
        object_type=object_type,
        object_url=object_url,
        permission=permission_name,
    )

    user_atomic_permission = UserAtomicPermission.objects.create(
        user=user, atomic_permission=atomic_permission, reason=reason
    )
    return user_atomic_permission


def add_permission_for_behandelaar(
    rol: Union[str, Rol]
) -> Optional[UserAtomicPermission]:
    if not isinstance(rol, Rol):
        rol = fetch_rol(rol)

    if not (
        rol.betrokkene_type == "medewerker"
        and rol.omschrijving_generiek == "behandelaar"
        and rol.betrokkene_identificatie
    ):
        return

    rol_username = rol.betrokkene_identificatie["identificatie"]
    if not User.objects.filter(username=rol_username).exists():
        return

    user = User.objects.get(username=rol_username)
    user_atomic_permission = add_atomic_permission_to_user(
        user, rol.zaak, reason=PermissionReason.betrokkene
    )
    return user_atomic_permission


def add_permissions_for_advisors(
    review_request: ReviewRequest,
) -> List[UserAtomicPermission]:

    user_deadlines = review_request.user_deadlines or {}
    rr_usernames = list(user_deadlines.keys())
    rr_users = User.objects.filter(username__in=rr_usernames)
    zaak_url = (
        review_request.for_zaak.url
        if isinstance(review_request.for_zaak, Zaak)
        else review_request.for_zaak
    )
    reason = (
        PermissionReason.accordeur
        if review_request.review_type == KownslTypes.approval
        else PermissionReason.adviseur
    )
    user_atomic_permissions = []
    for user in rr_users:
        user_atomic_permission = add_atomic_permission_to_user(
            user, zaak_url, reason=reason
        )
        if user_atomic_permission:
            user_atomic_permissions.append(user_atomic_permission)

    return user_atomic_permissions
