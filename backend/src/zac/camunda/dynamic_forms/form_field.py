import functools
import warnings
from abc import ABC
from typing import Dict, Optional, Tuple, Type

from rest_framework import serializers

from zac.api.polymorphism import SerializerCls

from ..data import Task

REGISTRY_INPUT_TYPES: Dict[str, Tuple[callable, SerializerCls]] = {}


class FormFieldContext(ABC):
    """
    Base class for form field context.

    The form field subclass is determined by the input_type.
    """

    pass


def get_form_field_context(input_type: str, **kwargs) -> Optional[FormFieldContext]:
    """
    Retrieve the form field specific context for a given form field.

    Consult the registry mapping form keys to specific context-determination functions.
    If no callback exists for a given input_type key, ``None`` is returned.

    Third party or non-core apps can add input_type keys to the registry by importing the
    ``REGISTRY`` constant and registering their input_type key with the appropriate callback
    callable.
    """
    (callback, *rest) = REGISTRY_INPUT_TYPES.get(f"zac:form_field:{input_type}")
    if callback is None:
        return None
    return callback(input_type, **kwargs)


class DuplicateInputTypeWarning(Warning):
    pass


def register_input_type(input_type: str, serializer_cls: Type[serializers.Serializer]):
    """
    Register the form key with the given callback and serializer class.
    """

    def decorator(func: callable):
        if input_type in REGISTRY_INPUT_TYPES:
            print(REGISTRY_INPUT_TYPES)
            warnings.warn(
                f"Overwriting existing input type '{input_type}' in registry.",
                DuplicateInputTypeWarning,
            )

        REGISTRY_INPUT_TYPES[input_type] = (func, serializer_cls)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

    return decorator
