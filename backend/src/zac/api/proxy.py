"""
Serializer class proxying another API, which *may* add additional data.
"""

from rest_framework import serializers


class ProxySerializer(serializers.Serializer):
    def to_representation(self, instance: dict):
        extra = super().to_representation(instance)
        return {**instance, **extra}
