from typing import Optional

from rest_framework import serializers

from ..models import LandingPageConfiguration, LandingPageLink, LandingPageSection


class LandingPageLinkSerializer(serializers.Serializer):
    icon = serializers.CharField()
    label = serializers.CharField()
    href = serializers.CharField()

    class Meta:
        models = LandingPageLink


class LandingPageSectionSerializer(serializers.Serializer):
    name = serializers.CharField()
    icon = serializers.CharField()
    links = LandingPageLinkSerializer(many=True)

    class Meta:
        model = LandingPageSection


class LandingPageConfigurationSerializer(serializers.Serializer):
    title = serializers.CharField()
    image = serializers.SerializerMethodField()
    sections = LandingPageSectionSerializer(many=True)
    links = LandingPageLinkSerializer(many=True)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super().__init__(*args, **kwargs)

    def get_image(self, obj) -> Optional[str]:
        if obj.image:
            return self.request.build_absolute_uri(obj.image.url)
        return None

    class Meta:
        model = LandingPageConfiguration
