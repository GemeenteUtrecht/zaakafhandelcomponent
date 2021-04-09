from typing import Any, Dict, Iterator, List

from django.utils.translation import gettext_lazy as _

from drf_spectacular.plumbing import force_instance
from drf_spectacular.utils import OpenApiParameter
from rest_framework import fields, serializers


def input_serializer_to_parameters(
    serializer: serializers.Serializer,
) -> List[OpenApiParameter]:
    serializer = force_instance(serializer)
    parameters = []

    for field in serializer.fields.values():
        if isinstance(field, serializers.HiddenField):
            continue

        if isinstance(field, serializers.Serializer):
            # querystring parameters only accept flat structures
            continue

        parameter = OpenApiParameter(
            name=field.field_name,
            type=str,
            location=OpenApiParameter.QUERY,
            required=field.required,
            description=field.help_text,
            enum=getattr(field, "choices", None),
        )
        parameters.append(parameter)

    return parameters


def check_if_field_is_valid(field: fields.Field) -> bool:
    """
    This makes sure we can only sort on fields that are required
    and valid.

    Examples of invalid fields (for now) are fields that are lists of
    nested objects (i.e., a field that is a serializer with
    many=True or a DictField).
    """
    if not field.required:
        return False

    else:
        if hasattr(field, "child"):
            # If the child is not explicitly set or the child is a serializer (why tho?) -> invalid
            if not field.child or isinstance(field.child, (serializers.Serializer)):
                return False

        if hasattr(field, "many"):
            if field.many:
                return False

    return True


def get_sorting_fields(fields: Dict[str, Any]) -> Iterator[str]:
    """
    This lists all the (nested) fields that can be sorted on.

    A field has to pass the check_if_valid_is_valid to be listed.
    """
    for field_name, field in fields.items():
        if check_if_field_is_valid(field):
            if isinstance(field, serializers.Serializer):
                nested_fields = get_sorting_fields(field.fields)

                # If nested objects don't have any valid fields - don't yield.
                for nested_field in nested_fields:
                    yield f"{field_name}.{nested_field}"
            else:
                yield field_name
        else:
            continue


def serializer_to_sorting_parameters(
    serializer: serializers.Serializer,
) -> OpenApiParameter:
    """
    Turns the serializer fields to possible sorting parameters.

    """
    serializer = force_instance(serializer)
    enum = list(get_sorting_fields(serializer.fields))

    return OpenApiParameter(
        name="sorting",
        type=str,
        location=OpenApiParameter.QUERY,
        required=False,
        description="Possible sorting parameters. Multiple values are possible and should be separated by a comma.",
        enum=enum,
    )
