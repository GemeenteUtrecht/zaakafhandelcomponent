import logging
from datetime import date
from typing import Optional, Set, Union

from django.core.exceptions import PermissionDenied

import rules
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Zaak

from zac.accounts.constants import AccessRequestResult
from zac.accounts.models import User
from zac.accounts.permissions import Permission, UserPermissions, register

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
from .views.utils import check_document_permissions

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


def _get_oos_from_zt_perms(
    user_perms: UserPermissions, zaaktype: str, va: str
) -> Set[str]:
    if user_perms.user.is_superuser:
        return {None}

    perm_oos = {
        zt_perm.oo
        for zt_perm in user_perms.zaaktype_permissions
        if (
            zt_perm.contains(zaaktype)
            and zt_perm.permission == zaken_inzien.name
            and zt_perm.test_va(va)
        )
    }
    return perm_oos


# TODO: extensive unit testing :-)
def test_oo_allowlist(user: User, zaak: Zaak) -> bool:
    """
    Test if the user and the zaak have an Organisatieonderdeel in common.

    Note that you should validate the actual permission for the zaak.zaaktype and VA
    before doing the OO check.
    """
    from zac.core.services import get_rollen

    zaaktype_url = zaak.zaaktype
    if not isinstance(zaaktype_url, str):
        zaaktype_url = zaaktype_url.url

    # OO is specced on the Authorization Profile level, and we grab the permissions
    # that are relevant to this zaaktype. We can therefore union the OO-sets on each
    # permission. OO filtering on Authorization profile level is additive - if one AP
    # gives access to OO1 zaken, and another AP gives access to OO2 zaken from the
    # same zaaktype, then the user can see the zaak as soon as it belongs to any of
    # OO1 or OO2 (provided that user is member of both APs).
    relevant_oos: set = _get_oos_from_zt_perms(
        UserPermissions(user),
        zaaktype_url,
        zaak.vertrouwelijkheidaanduiding,
    )

    # shortcut - as soon as there is a single AP that is NOT OO bound/scoped, it means
    # no filtering on OO should take place. This effectively means that there is an AP
    # granting permission to all zaken of the zaak.zaaktype (within the max_va).
    if None in relevant_oos:
        return True

    # finally, check that the zaak belongs to the allowed OOs
    rollen = get_rollen(zaak)
    relevant_roles = [
        rol
        for rol in rollen
        if rol.betrokkene_type == "organisatorische_eenheid"
        and rol.betrokkene_identificatie.get("identificatie") in relevant_oos
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
    from .services import get_rollen

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


@rules.predicate
def can_download_document(user: User, document: Document) -> bool:

    try:
        check_document_permissions(document, user)
    except PermissionDenied:
        return False

    return True


rules.add_rule("zaken:afhandelen", can_close_zaken | can_set_results)
rules.add_rule(zaken_inzien.name, can_read_zaak_by_zaaktype | has_temporary_access)
rules.add_rule(
    zaken_handle_access.name, can_handle_zaak_by_zaaktype & is_zaak_behandelaar
)
rules.add_rule("core:download_document", can_download_document)
