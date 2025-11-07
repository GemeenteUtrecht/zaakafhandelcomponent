"""
Provide polymorphic serializer base class.

Polymorphism happens when a resource takes a certain shape depending on the type
of the resource. Usually they have a common base type. The exact type/shape is not
statically known, but depends on the run-time values.

Note that we cannnot use https://github.com/apirobot/django-rest-polymorphic because
it builds on the django-polymorphic Model, which we don't use since our data
is retrieved from upstream APIs.

The implementation is inspired on the vng-api-common implementation:
https://github.com/VNG-Realisatie/vng-api-common/blob/master/vng_api_common/polymorphism.py

Note that the discriminator field must exist at the same depth as the mapped serializer
fields for the OpenAPI introspection. See
https://swagger.io/docs/specification/data-models/inheritance-and-polymorphism/ for
more information. As such, it's not possible to define something like:

{
    "object_type": "foo",
    "polymorphic_context": {
        <foo-specific fields>
    }
}

without explicitly wrapping this in a parent serializer, i.e. - ``polymorphic_context``
can not be a PolymorphicSerializer itself, as it requires access to the ``object_type``
in the parent scope.
"""

import warnings
from typing import Dict, Optional, Type, Union

from django.core.exceptions import ImproperlyConfigured

from rest_framework import serializers
from rest_framework.fields import empty

SerializerCls = Type[serializers.Serializer]
SerializerClsOrInstance = Union[serializers.Serializer, SerializerCls]
Primitive = Union[str, int, float]


class HiddenDiscriminatorField(serializers.HiddenField):
    """
    This field checks for the existence of another field.
    If it exists the value defaults to True, otherwise False.

    """

    related_field = None

    def _field_exists(self) -> bool:
        return bool(self.parent.initial_data.get(self.get_related_field()))

    def __init__(self, *args, **kwargs):
        kwargs["default"] = self._field_exists
        self.related_field = kwargs.pop("related_field", None)
        super().__init__(*args, **kwargs)

    def get_related_field(self):
        if not self.related_field:
            raise ImproperlyConfigured("`related_field` kwarg must be set on field.")
        return self.related_field


class PolymorphicSerializer(serializers.Serializer):
    # mapping of discriminator value to serializer (instance or class)
    serializer_mapping: Optional[Dict[Primitive, SerializerClsOrInstance]] = None

    # the serializer field that holds the discriminator values
    discriminator_field = "object_type"
    fallback_distriminator_value = None
    strict = True

    def __new__(cls, *args, **kwargs):
        if cls.serializer_mapping is None:
            raise ImproperlyConfigured(
                "`{cls}` is missing a `{cls}.serializer_mapping` attribute".format(
                    cls=cls.__name__
                )
            )

        if not isinstance(cls.discriminator_field, str):
            raise ImproperlyConfigured(
                "`{cls}.discriminator_field` must be a string".format(cls=cls.__name__)
            )

        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        serializer_mapping = self.serializer_mapping
        self.serializer_mapping = {}

        for object_type, serializer in serializer_mapping.items():
            if callable(serializer):
                serializer = serializer(*args, **kwargs)
                serializer.parent = self

            self.serializer_mapping[object_type] = serializer

    def to_representation(self, instance):
        default = super().to_representation(instance)
        serializer = self._get_serializer_from_instance(instance)
        extra = serializer.to_representation(instance)
        return {**default, **extra}

    def to_internal_value(self, data):
        default = super().to_internal_value(data)
        serializer = self._get_serializer_from_data(data)
        extra = serializer.to_internal_value(data)
        return {**default, **extra}

    def is_valid(self, *args, **kwargs):
        valid = super().is_valid(*args, **kwargs)
        extra_serializer = self._get_serializer_from_data(self.data)
        if hasattr(self, "_data"):
            setattr(extra_serializer, "_data", self.data)
        extra_valid = extra_serializer.is_valid(*args, **kwargs)
        self._errors.update(extra_serializer.errors)
        return valid and extra_valid

    def run_validation(self, data=empty):
        value = super().run_validation(data=data)
        extra_serializer = self._get_serializer_from_data(data)
        validated_data = extra_serializer.run_validation(data)
        return {**value, **validated_data}

    def _check_discriminator_value(self, discriminator_value: str) -> str:
        if (
            discriminator_value not in self.serializer_mapping
            and self.fallback_distriminator_value is not None
        ):
            warnings.warn(
                f"Discriminator value {discriminator_value} missing from mapping, "
                f"falling back to {self.fallback_distriminator_value}",
                RuntimeWarning,
            )
            return self.fallback_distriminator_value

        return discriminator_value

    def _discriminator_serializer(self, discriminator_value: str):
        discriminator_value = self._check_discriminator_value(discriminator_value)
        try:
            return self.serializer_mapping[discriminator_value]
        except KeyError as exc:
            if self.strict:
                raise KeyError(
                    "`{cls}.serializer_mapping` is missing a corresponding serializer "
                    "for the `{value}` key".format(
                        cls=self.__class__.__name__,
                        value=discriminator_value,
                    )
                ) from exc
            else:
                return serializers.Serializer()

    def _get_serializer_from_data(self, data):
        field = self.fields[self.discriminator_field]

        # for PATCH
        if self.instance:
            discriminator_value = field.get_attribute(self.instance)
        else:
            if type(field) != HiddenDiscriminatorField:
                discriminator_value = field.get_value(data)
            else:
                discriminator_value = field.get_default()
        serializer = self._discriminator_serializer(discriminator_value)
        return serializer

    def _get_serializer_from_instance(self, instance):
        discriminator_value = self.fields[self.discriminator_field].get_attribute(
            instance
        )
        serializer = self._discriminator_serializer(discriminator_value)
        return serializer


class GroupPolymorphicSerializer(PolymorphicSerializer):
    """
    polymorhic fields are grouped into one particular field
    """

    group_field = None
    group_field_kwargs = {}

    def _discriminator_serializer(self, discriminator_value: str):
        serializer = super()._discriminator_serializer(discriminator_value)

        group_name = f"{self.group_field.capitalize()}{serializer.__class__.__name__}"
        group_field = serializer.__class__(**self.group_field_kwargs)
        group_serializer_class = type(
            group_name,
            (serializers.Serializer,),
            {self.group_field: group_field},
        )
        return group_serializer_class()
