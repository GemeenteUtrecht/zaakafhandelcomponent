from rest_framework import serializers


class RecursiveField(serializers.Serializer):
    def to_representation(self, instance):
        return self.parent.parent.to_representation(instance)


class TaskSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(max_length=100)
    created = serializers.DateTimeField()
    has_form = serializers.BooleanField()
    # todo replace with user serializer
    assignee = serializers.CharField()


class ProcessInstanceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    definition_id = serializers.CharField(max_length=1000)
    sub_processes = RecursiveField(many=True)
    messages = serializers.ListField(
        child=serializers.CharField(max_length=100), allow_empty=True
    )
    tasks = TaskSerializer(many=True)
