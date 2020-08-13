from rest_framework import serializers


class InformatieObjectTypeSerializer(serializers.Serializer):
    url = serializers.URLField()
    omschrijving = serializers.CharField()
