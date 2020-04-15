from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import NotificatieSerializer


class NotificationCallbackView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = NotificatieSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.handle_notification(serializer.data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def handle_notification(self, data: dict):
        import bpdb

        bpdb.set_trace()
