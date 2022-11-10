from rest_framework import permissions, views
from rest_framework.response import Response

from ..models import LandingPageConfiguration
from .serializers import LandingPageConfigurationSerializer


class LandingPageConfigurationView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = LandingPageConfigurationSerializer

    def get_serializer(self, *args, **kwargs):
        return self.serializer_class(*args, **{**kwargs, "request": self.request})

    def get_object(self) -> LandingPageConfiguration:
        return LandingPageConfiguration.get_solo()

    def get(self, request, *args, **kwargs):
        """
        Retrieve the landing page configuration.
        """
        instance = self.get_object()
        return Response(self.get_serializer(instance).data)
