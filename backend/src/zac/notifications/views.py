from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .routing import handler
from .serializers import NotificatieSerializer


class BaseNotificationCallbackView(APIView):
    schema = None

    def post(self, request, *args, **kwargs):
        serializer = NotificatieSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.handle_notification(serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def handle_notification(self, data: dict) -> None:
        raise NotImplementedError("Subclasses must implement 'handle_notification'")


class NotificationCallbackView(BaseNotificationCallbackView):
    def handle_notification(self, data: dict) -> None:
        handler.handle(data)
