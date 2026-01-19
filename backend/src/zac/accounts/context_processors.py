from typing import Dict

from django.http import HttpRequest

from .api.serializers import UserSerializer


def user_serializer(request: HttpRequest) -> Dict[str, UserSerializer]:
    """
    Add a user serializer to the context for JSON data access.
    """
    return {
        "user_serializer": UserSerializer(instance=request.user),
    }
