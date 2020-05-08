import functools
from collections import defaultdict
from dataclasses import dataclass
from typing import List

from django.core.exceptions import ImproperlyConfigured

import rules
from zgw_consumers.api_models.catalogi import ZaakType

from .datastructures import VA_ORDER, ZaakPermissionCollection
from .models import User

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


# Deprecated
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

        valid_urls = self.zaaktype_permissions.zaaktype_urls
        return [zt for zt in zaaktypen if zt.url in valid_urls]

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
