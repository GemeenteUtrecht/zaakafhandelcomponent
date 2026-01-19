from django.utils.translation import gettext_lazy as _

from rest_framework.utils import formatting

from zac.api.polymorphism import SerializerCls
from zac.tests.compat import APIModelSerializer


def usertask_context_serializer(serializer_cls: SerializerCls) -> SerializerCls:
    """
    Ensure that the Context-specific serializer is wrapped in a UserTaskData serializer.

    The decorator enforces the same label/help_text and meta-information for the API
    schema documentation.
    """
    from .data import UserTaskData

    name = serializer_cls.__name__
    name = formatting.remove_trailing_string(name, "Serializer")
    name = formatting.remove_trailing_string(name, "Context")

    class TaskDataSerializer(APIModelSerializer):
        context = serializer_cls(
            label=_("User task context"),
            help_text=_(
                "The task context shape depends on the `form` property. The value will be "
                "`null` if the backend does not 'know' the user task `formKey`."
            ),
            allow_null=True,
        )

        class Meta:
            dataclass = UserTaskData
            fields = ("context",)

    name = f"{name}TaskDataSerializer"
    return type(name, (TaskDataSerializer,), {})
