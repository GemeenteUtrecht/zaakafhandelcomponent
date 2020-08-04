from rest_framework import serializers

from zac.accounts.serializers import UserSerializer


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
