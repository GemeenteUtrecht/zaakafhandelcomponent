from typing import Type

from rest_framework import relations
from rest_framework.serializers import Serializer

from zac.accounts.api.serializers import GroupSerializer, UserSerializer


class SerializerSlugRelatedField(relations.SlugRelatedField):
    response_serializer = None

    def get_response_serializer(self, obj: object) -> Type[Serializer]:
        assert self.response_serializer
        return self.response_serializer(obj)

    def to_representation(self, obj):
        return self.get_response_serializer(obj).data


class UserSlugRelatedField(SerializerSlugRelatedField):
    response_serializer = UserSerializer


class GroupSlugRelatedField(SerializerSlugRelatedField):
    response_serializer = GroupSerializer
