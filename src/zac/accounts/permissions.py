from collections import defaultdict
from dataclasses import dataclass
from typing import List, Optional

from django.db.models import Max

from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from .models import PermissionSet, User

VA_ORDER = {
    value: VertrouwelijkheidsAanduidingen.get_choice(value).order
    for value, _ in VertrouwelijkheidsAanduidingen.choices
}


@dataclass
class Permission:
    name: str
    description: str


class Registry:
    def __init__(self):
        self._registry = {}

    def __call__(self, perm: Permission):
        """
        Register a permission class.
        """
        self._registry[perm.name] = perm
        return perm


@dataclass
class ZaaktypePermission:
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


@dataclass
class UserPermissions:
    user: User

    @property
    def zaaktype_permissions(self):
        """
        Translate the database permission sets for the user into Python objects.

        This keeps a registry of the permissions pinned to a particular zaaktype, and
        caches it on the instance. UserPermission objects are intantiated for every
        request, so the cache is contained in the request-response cycle.
        """
        if not hasattr(self, "_zaaktype_perms"):
            _zt_perms = {}

            perm_sets = PermissionSet.objects.filter(
                authorizationprofile__user=self.user
            )
            for perm_set in perm_sets:
                for identificatie in perm_set.zaaktype_identificaties:
                    unique_id = (perm_set.catalogus, identificatie)
                    if unique_id not in _zt_perms:
                        _zt_perms[unique_id] = perm_set.max_va
                    else:
                        current_order = VA_ORDER[_zt_perms[unique_id]]
                        perm_order = VA_ORDER[perm_set.max_va]
                        if perm_order > current_order:
                            _zt_perms[unique_id] = perm_set.max_va

            self._zaaktype_perms = [
                ZaaktypePermission(
                    catalogus=catalogus_url, identificatie=identificatie, max_va=max_va,
                )
                for (catalogus_url, identificatie), max_va in _zt_perms.items()
            ]

        return self._zaaktype_perms

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


register = Registry()
