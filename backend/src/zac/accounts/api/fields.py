from rest_framework.serializers import Serializer

from zac.accounts.api.serializers import GroupSerializer, UserSerializer
from zac.accounts.models import User
from zac.core.api.fields import SerializerSlugRelatedField


class UserSlugRelatedField(SerializerSlugRelatedField):
    response_serializer = UserSerializer


class GroupSlugRelatedField(SerializerSlugRelatedField):
    response_serializer = GroupSerializer


class UserSlugSerializer(Serializer):
    user = UserSlugRelatedField(
        slug_field="username",
        queryset=User.objects.prefetch_related("groups").all(),
        allow_null=True,
        required=True,
    )
