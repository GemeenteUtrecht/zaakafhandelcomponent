from rest_framework import serializers


class RecursiveField(serializers.Serializer):
    def to_representation(self, instance):
        return self.parent.parent.to_representation(instance)


class ProcessInstanceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    definition_id = serializers.CharField(max_length=1000)
    sub_processes = RecursiveField(many=True)
