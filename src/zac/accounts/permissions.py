import functools
import itertools
from collections import defaultdict
from dataclasses import dataclass
from typing import List

from django.core.exceptions import ImproperlyConfigured

import rules
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from .models import PermissionSet, User

VA_ORDER = {
    value: VertrouwelijkheidsAanduidingen.get_choice(value).order
    for value, _ in VertrouwelijkheidsAanduidingen.choices
}


registry = {}


@dataclass(frozen=True)
class Permission:
    name: str
    description: str

    def __post_init__(self):
        if self.name in registry:
            raise ImproperlyConfigured(
                "Permission with name '{self.name}' already exists"
            )
        registry[self.name] = self

    def __hash__(self):
        return hash(self.name)


@dataclass
class ZaaktypePermission:
    permission: str
    catalogus: str
    identificatie: str
    max_va: str

    @property
    def zaaktypen(self) -> List[ZaakType]:
        from zac.core.services import get_zaaktypen

        if not hasattr(self, "_zaaktypen"):
            zts = get_zaaktypen(catalogus=self.catalogus)
            self._zaaktypen = [
                zt for zt in zts if zt.identificatie == self.identificatie
            ]
        return self._zaaktypen

    def contains(self, url: str) -> bool:
        return any(zaaktype.url == url for zaaktype in self.zaaktypen)

    def test_va(self, other_va: str) -> bool:
        va_nr = VA_ORDER[self.max_va]
        other_va_nr = VA_ORDER[other_va]
        return va_nr >= other_va_nr


class ZaakPermissionCollection:
    def __init__(self, perms: List[ZaaktypePermission]):
        self._perms = perms

        # build an index on permission
        self._permissions = {}
        for perm in sorted(self._perms, key=lambda perm: perm.permission):
            for perm_key, _perms in itertools.groupby(
                self._perms, key=lambda perm: perm.permission
            ):
                self._permissions[perm_key] = list(_perms)

    def __iter__(self):
        return iter(self._perms)

    @classmethod
    def for_user(cls, user):
        """
        Query the database for the permissions for a user.

        Factory method to create the permissions collection to test a user's
        permissions.
        """
        _zt_perms = {}

        perm_sets = PermissionSet.objects.filter(authorizationprofile__user=user)
        for perm_set in perm_sets:
            for perm_key in perm_set.permissions:
                for identificatie in perm_set.zaaktype_identificaties:
                    unique_id = (perm_key, perm_set.catalogus, identificatie)
                    if unique_id not in _zt_perms:
                        _zt_perms[unique_id] = perm_set.max_va
                    else:
                        current_order = VA_ORDER[_zt_perms[unique_id]]
                        perm_order = VA_ORDER[perm_set.max_va]
                        if perm_order > current_order:
                            _zt_perms[unique_id] = perm_set.max_va

        return cls(
            [
                ZaaktypePermission(
                    permission=perm_key,
                    catalogus=catalogus_url,
                    identificatie=identificatie,
                    max_va=max_va,
                )
                for (
                    perm_key,
                    catalogus_url,
                    identificatie,
                ), max_va in _zt_perms.items()
            ]
        )

    def contains(
        self, permission: str, zaaktype: str, vertrouwelijkheidaanduiding: str
    ):
        # user does not have permission at all
        if permission not in self._permissions:
            return False

        # filter out permission objects that do not apply (different permission) or
        # already are limited in VA
        _relevant_perms = [
            perm
            for perm in self._permissions[permission]
            if perm.test_va(vertrouwelijkheidaanduiding)
        ]
        if not _relevant_perms:
            return False

        return any(perm.contains(zaaktype) for perm in _relevant_perms)


@dataclass
class UserPermissions:
    user: User

    @property
    def zaaktype_permissions(self):
        if not hasattr(self.user, "_zaaktype_perms"):
            self.user._zaaktype_perms = ZaakPermissionCollection.for_user(self.user)
        return self.user._zaaktype_perms

    def filter_zaaktypen(self, zaaktypen: List[ZaakType]) -> List[ZaakType]:
        """
        Given a full list of zaaktypen, return the subset that the user has access to.
        """
        if self.user.is_superuser:
            return zaaktypen

        ids_per_catalogus = defaultdict(list)
        has_all = defaultdict(bool)

        qs = self.user.auth_profiles.values_list(
            "permission_sets__catalogus", "permission_sets__zaaktype_identificaties"
        )
        for catalogus_url, ids in qs:
            if len(ids) == 0:
                has_all[catalogus_url] = True
            else:
                ids_per_catalogus[catalogus_url] += ids

        allowed = []
        for zaaktype in zaaktypen:
            catalogus_url = zaaktype.catalogus
            if has_all[catalogus_url]:
                allowed.append(zaaktype)
            elif zaaktype.identificatie in ids_per_catalogus[catalogus_url]:
                allowed.append(zaaktype)

        return allowed

    def test_zaak_access(self, zaaktype: str, va: str) -> bool:
        if self.user.is_superuser:
            return True

        zaaktype_perm = next(
            (
                zt_perm
                for zt_perm in self.zaaktype_permissions
                if zt_perm.contains(zaaktype)
            ),
            None,
        )
        if zaaktype_perm is None:  # permission on zaaktype found
            return False

        # lower number means more public
        zaak_va = VA_ORDER[va]
        required_va = VA_ORDER[zaaktype_perm.max_va]
        return zaak_va <= required_va


def register(*permissions: Permission):
    """
    Register a permission with a generic predicate check.
    """

    def wrapper_factory(func, permission):
        @functools.wraps(func)
        def wrapper(user, obj):
            return func(user, obj, permission)

        return wrapper

    def decorator(func):

        for permission in permissions:
            wrapper = wrapper_factory(func, permission)
            predicate = rules.predicate(wrapper)
            rules.add_rule(permission.name, predicate)

        # keep unmodified original callable
        return func

    return decorator
