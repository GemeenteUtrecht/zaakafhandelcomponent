from django.db import transaction
from django.utils.translation import gettext_lazy as _

from django_camunda.api import complete_task
from rest_framework import permissions, status, views
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.settings import api_settings

from ..models import UserTaskCallback


class CallbackView(views.APIView):
    permission_classes = (permissions.AllowAny,)
    # TODO: throttle

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            callback = UserTaskCallback.objects.get(callback_id=kwargs["callback_id"])
        except UserTaskCallback.DoesNotExist:
            raise ValidationError(
                {api_settings.NON_FIELD_ERRORS_KEY: _("Invalid callback URL given.")}
            )

        if callback.callback_received:
            raise ValidationError(
                {api_settings.NON_FIELD_ERRORS_KEY: _("Callback was already received.")}
            )

        callback.callback_received = True
        callback.save()

        # TODO process request.data
        complete_task(callback.task_id, request.data.items())

        return Response(status=status.HTTP_204_NO_CONTENT)
