import functools
import warnings
from abc import ABC
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Type

from rest_framework import parsers, renderers, serializers

from zac.api.polymorphism import SerializerCls

from ..data import Task
from .drf import usertask_context_serializer

Parsers = Tuple[Type[parsers.BaseParser]]
Renderers = Tuple[Type[renderers.BaseRenderer]]


@dataclass
class RegistryItem:
    callback: callable
    read_serializer: SerializerCls
    write_serializer: Optional[SerializerCls] = None
    parsers: Optional[Parsers] = None
    renderers: Optional[Renderers] = None


REGISTRY: Dict[str, RegistryItem] = {}


class Context(ABC):
    """
    Base class for user-task contexts.

    The user task context subclass is determined by the form_key.
    """

    pass


def get_registry_item(task: Task) -> RegistryItem:
    lookup = task.form_key
    if task.form_key not in REGISTRY:
        warnings.warn(
            f"Unknown task registry key: '{lookup}'. Falling back to dynamic form.",
            RuntimeWarning,
        )
        lookup = ""

    return REGISTRY.get(lookup)


def get_context(task: Task) -> Optional[Context]:
    """
    Retrieve the task-specific context for a given user task.

    Consult the registry mapping form keys to specific context-determination functions.
    If no callback exists for a given form key, ``None`` is returned.

    Third party or non-core apps can add form keys to the registry by importing the
    ``REGISTRY`` constant and registering their form key with the appropriote callback
    callable.
    """
    item = get_registry_item(task)
    if item.callback is None:
        return None
    return item.callback(task)


class DuplicateFormKeyWarning(Warning):
    pass


def register(
    form_key: str,
    read_serializer_cls: SerializerCls,
    write_serializer_cls: Optional[SerializerCls] = None,
    parsers: Optional[Parsers] = None,
    renderers: Optional[Renderers] = None,
):
    """
    Register the form key with the given callback and serializer class.
    """

    def decorator(func: callable):
        if form_key in REGISTRY:
            warnings.warn(
                f"Overwriting existing form key '{form_key}' in registry.",
                DuplicateFormKeyWarning,
            )

        REGISTRY[form_key] = RegistryItem(
            callback=func,
            read_serializer=read_serializer_cls,
            write_serializer=write_serializer_cls,
            parsers=parsers,
            renderers=renderers,
        )

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


EmptySerializer = usertask_context_serializer(serializers.JSONField)
