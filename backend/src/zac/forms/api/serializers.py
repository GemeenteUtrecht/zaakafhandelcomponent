from rest_framework import serializers


class FormSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.SlugField()
    layouts = serializers.ListField(child=serializers.CharField())
