from typing import List, Optional, Union

from zac.contrib.kownsl.data import ReviewRequest
from zac.core.permissions import zaken_inzien
from zac.core.rollen import Rol
from zac.core.services import fetch_rol
from zgw.models.zrc import Zaak

from .constants import PermissionObjectType
from .models import AtomicPermission, User


def add_atomic_permission_to_user(
    user: User,
    object_url: str,
    object_type: str = PermissionObjectType.zaak,
    permission_name: str = zaken_inzien.name,
) -> Optional[AtomicPermission]:
    if (
        AtomicPermission.objects.for_user(user)
        .actual()
        .filter(
            object_type=object_type,
            object_url=object_url,
            permission=permission_name,
        )
        .exists()
    ):
        return None

    atomic_permission = AtomicPermission.objects.create(
        object_type=object_type,
        object_url=object_url,
        permission=permission_name,
    )
    user.atomic_permissions.add(atomic_permission)
    return atomic_permission


def add_permission_for_behandelaar(rol: Union[str, Rol]) -> Optional[AtomicPermission]:
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
    atomic_permission = add_atomic_permission_to_user(user, rol.zaak)
    return atomic_permission


def add_permissions_for_advisors(
    review_request: ReviewRequest,
) -> List[AtomicPermission]:

    user_deadlines = review_request.user_deadlines or {}
    rr_usernames = list(user_deadlines.keys())
    rr_users = User.objects.filter(username__in=rr_usernames)
    zaak_url = (
        review_request.for_zaak.url
        if isinstance(review_request.for_zaak, Zaak)
        else review_request.for_zaak
    )
    atomic_permissions = []
    for user in rr_users:
        atomic_permission = add_atomic_permission_to_user(user, zaak_url)
        if atomic_permission:
            atomic_permissions.append(atomic_permission)

    return atomic_permissions
