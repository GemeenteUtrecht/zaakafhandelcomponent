from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..client import OpenFormsClient
from .serializers import FormSerializer


class FormListView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = FormSerializer

    def get_serializer(self, **kwargs):
        return self.serializer_class(many=True, **kwargs)

    def get(self, request, format=None):
        client = OpenFormsClient()
        definitions = client.get_forms()
        serializer = self.get_serializer(instance=definitions)
        return Response(serializer.data)
