from dataclasses import dataclass


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


register = Registry()
