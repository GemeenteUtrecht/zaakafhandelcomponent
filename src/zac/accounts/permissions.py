from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List

from zgw_consumers.api_models.catalogi import ZaakType

from .models import User


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
class UserPermissions:
    user: User

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


register = Registry()
