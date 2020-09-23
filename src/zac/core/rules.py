import logging
from datetime import date
from typing import Optional, Union

import rules
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.zaken import Zaak

from zac.accounts.constants import AccessRequestResult
from zac.accounts.models import User
from zac.accounts.permissions import Permission, register
from zac.core.services import get_rollen

from .permissions import (
    zaakproces_send_message,
    zaakproces_usertasks,
    zaken_add_documents,
    zaken_close,
    zaken_handle_access,
    zaken_inzien,
    zaken_request_access,
    zaken_set_result,
)
from .services import get_rollen

logger = logging.getLogger(__name__)


@register(
    zaakproces_send_message,
    zaakproces_usertasks,
    zaken_set_result,
    zaken_close,
    zaken_add_documents,
    zaken_request_access,
)
def _generic_zaakpermission(
    user: User, zaak: Union[dict, Zaak], permission: Permission
):
    logger.debug("Checking permission %r for user %r", permission, user)

    if isinstance(zaak, dict):
        zaak: Zaak = factory(Zaak, zaak)

    zaaktype_url = zaak.zaaktype
    if not isinstance(zaaktype_url, str):
        zaaktype_url = zaaktype_url.url

    permissions = user._zaaktype_perms
    has_permission_at_all = permissions.contains(
        permission=permission.name,
        zaaktype=zaaktype_url,
        vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding,
    )
    if not has_permission_at_all:
        return False

    # check if it's restricted by OO
    oo_allowed = test_oo_allowlist(user, zaak)
    return oo_allowed


def _has_permission_key(permission_name: str, user: User):
    available_perms = user._zaaktype_perms._permissions.keys()
    return permission_name in available_perms


# TODO: extensive unit testing :-)
def test_oo_allowlist(user: User, zaak: Zaak) -> bool:
    """
    Test if the user and the zaak have an Organisatieonderdeel in common.
    """
    zaaktype_url = zaak.zaaktype
    if not isinstance(zaaktype_url, str):
        zaaktype_url = zaaktype_url.url

    relevant_perms = [
        perm for perm in user._zaaktype_perms if perm.contains(zaaktype_url)
    ]

    # OOs that must intersect with the user OOs
    perm_oos = {perm.oo for perm in relevant_perms}

    # if there are no OO-based permissions at all, access is granted
    if not perm_oos:
        return True

    # check that the user has any of the OOs imposed by the permissions
    if not user.oos.filter(slug__in=perm_oos).exists():
        return False

    # finally, check that the zaak belongs to the allowed OOs
    rollen = get_rollen(zaak)
    relevant_roles = [
        rol
        for rol in rollen
        if rol.betrokkene_type == "organisatorische_eenheid"
        and rol.betrokkene_identificatie.get("identificatie") in perm_oos
    ]
    return any(relevant_roles)


@rules.predicate
def can_close_zaken(user: User, zaak: Optional[Zaak]):
    if zaak is None:
        return _has_permission_key(zaken_close.name, user)
    if zaak.einddatum:
        return False
    return _generic_zaakpermission(user, zaak, zaken_close)


@rules.predicate
def can_set_results(user: User, zaak: Optional[Zaak]):
    if zaak is None:
        return _has_permission_key(zaken_set_result.name, user)
    if zaak.einddatum:
        return False
    return _generic_zaakpermission(user, zaak, zaken_set_result)


@rules.predicate
def can_read_zaak_by_zaaktype(user: User, zaak: Optional[Zaak]):
    if zaak is None:
        return _has_permission_key(zaken_inzien.name, user)
    return _generic_zaakpermission(user, zaak, zaken_inzien)


@rules.predicate
def has_temporary_access(user: User, zaak: Optional[Zaak]):
    if zaak is None:
        return False
    return user.initiated_requests.filter(
        zaak=zaak.url, result=AccessRequestResult.approve, end_date__gte=date.today()
    ).exists()


@rules.predicate
def can_handle_zaak_by_zaaktype(user: User, zaak: Optional[Zaak]):
    if zaak is None:
        return _has_permission_key(zaken_handle_access.name, user)
    return _generic_zaakpermission(user, zaak, zaken_handle_access)


@rules.predicate
def is_zaak_behandelaar(user: User, zaak: Optional[Zaak]):
    if zaak is None:
        return True
    user_rollen = [
        rol
        for rol in get_rollen(zaak)
        if rol.omschrijving_generiek == "behandelaar"
        and rol.betrokkene_type == "medewerker"
        and rol.betrokkene_identificatie.get("identificatie") == user.username
    ]
    return bool(user_rollen)


rules.add_rule("zaken:afhandelen", can_close_zaken | can_set_results)
rules.add_rule(zaken_inzien.name, can_read_zaak_by_zaaktype | has_temporary_access)
rules.add_rule(
    zaken_handle_access.name, can_handle_zaak_by_zaaktype & is_zaak_behandelaar
)
