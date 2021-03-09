import functools
from dataclasses import dataclass
from typing import List, Optional

from django.core.exceptions import ImproperlyConfigured

import rules
from rest_framework.serializers import Serializer
from zgw_consumers.api_models.catalogi import ZaakType

from .datastructures import ZaakPermissionCollection
from .models import User

registry = {}


@dataclass(frozen=True)
class Policy:
    """
    class to manage blueprint permissions
    """

    serializer: Serializer

    def access_request(self, obj):
        raise NotImplementedError("This method must be implemented by a subclass")


@dataclass(frozen=True)
class Permission:
    name: str
    description: str
    policy: Optional[Policy] = None

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


def register(*permissions: Permission):
    """
    Register a permission with a generic predicate check.
    """

    def wrapper_factory(func, permission):
        @functools.wraps(func)
        def wrapper(user, obj):
            # this only deals with object-level permission checks
            if obj is None:
                return None
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
