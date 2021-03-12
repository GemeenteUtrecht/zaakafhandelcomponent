from typing import List, Optional, Union

from zgw_consumers.api_models.zaken import Zaak

from zac.contrib.kownsl.data import ReviewRequest
from zac.core.permissions import zaken_inzien
from zac.core.rollen import Rol
from zac.core.services import fetch_rol

from .constants import PermissionObjectType
from .models import PermissionDefinition, User


def add_atomic_permission_to_user(
    user: User,
    object_url: str,
    object_type: str = PermissionObjectType.zaak,
    permission_name: str = zaken_inzien.name,
) -> Optional[PermissionDefinition]:
    if (
        PermissionDefinition.objects.for_user(user)
        .actual()
        .filter(
            object_type=object_type,
            object_url=object_url,
            permission=permission_name,
        )
        .exists()
    ):
        return None

    permission_definition = PermissionDefinition.objects.create(
        object_type=object_type,
        object_url=object_url,
        permission=zaken_inzien.name,
    )
    user.permission_definitions.add(permission_definition)
    return permission_definition


def add_permission_for_behandelaar(
    rol: Union[str, Rol]
) -> Optional[PermissionDefinition]:
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
    permission_definition = add_atomic_permission_to_user(user, rol.zaak)
    return permission_definition


def add_permissions_for_advisors(
    review_request: ReviewRequest,
) -> List[PermissionDefinition]:

    user_deadlines = review_request.user_deadlines or {}
    rr_usernames = list(user_deadlines.keys())
    rr_users = User.objects.filter(username__in=rr_usernames)
    zaak_url = (
        review_request.for_zaak.url
        if isinstance(review_request.for_zaak, Zaak)
        else review_request.for_zaak
    )
    permission_definitions = []
    for user in rr_users:
        permission_definition = add_atomic_permission_to_user(user, zaak_url)
        if permission_definition:
            permission_definitions.append(permission_definition)

    return permission_definitions
