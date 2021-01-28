from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from zac.accounts.serializers import UserSerializer

from ..user_tasks import REGISTRY


class ErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()


class RecursiveField(serializers.Serializer):
    def to_representation(self, instance):
        return self.parent.parent.to_representation(instance)


class TaskSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    execute_url = serializers.URLField()
    name = serializers.CharField(max_length=100)
    created = serializers.DateTimeField()
    has_form = serializers.BooleanField()
    assignee = UserSerializer(allow_null=True, required=False)


class ProcessInstanceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    definition_id = serializers.CharField(max_length=1000)
    title = serializers.CharField(max_length=100)
    sub_processes = RecursiveField(many=True)
    messages = serializers.ListField(
        child=serializers.CharField(max_length=100), allow_empty=True
    )
    tasks = TaskSerializer(many=True)


class UserTaskContextSerializer(serializers.Serializer):
    form = serializers.ChoiceField(
        label=_("Form to render"),
        source="task.form_key",
        help_text=_(
            "The form key of the form to render. Note that unknown form keys (= not "
            "present in the enum) will be returned as is."
        ),
        allow_blank=True,
        choices=(),
    )
    task = TaskSerializer(label=_("User task summary"))
    context = serializers.JSONField(
        label=_("User task context"),
        help_text=_(
            "The task context shape depends on the `form` property. The value will be "
            "`null` if the backend does not 'know' the user task `formKey`."
        ),
        allow_null=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["form"].choices = list(REGISTRY.keys())
