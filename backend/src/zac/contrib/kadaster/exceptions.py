from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.exceptions import APIException


class KadasterAPIException(APIException):
    def __init__(
        self,
        detail=None,
        code="error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        super().__init__(detail=detail, code=code)
        self.status_code = status_code
