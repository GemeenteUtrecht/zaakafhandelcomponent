"""
Objects stored in the OBJECTS API will retain as much user and group information as possible.

"""

from typing import Dict, Union

from django.contrib.auth.models import Group
from django.utils.translation import gettext as _

from rest_framework import serializers

from zac.accounts.api.serializers import GroupSerializer, UserSerializer
from zac.accounts.models import Group, User
from zac.core.api.fields import SerializerSlugRelatedField

###################################################
#                Meta object users                #
###################################################


class MetaObjectUserSerializer(UserSerializer):
    full_name = serializers.SerializerMethodField(
        help_text=_("User-friendly full name of user.")
    )

    class Meta:
        model = UserSerializer.Meta.model
        fields = (
            "email",
            "first_name",
            "full_name",
            "last_name",
            "username",
        )

    def get_full_name(self, obj) -> str:
        full_name = ""
        if isinstance(obj, User):
            full_name = obj.get_full_name()
        else:
            full_name = obj.get("full_name", obj.get("username", "Onbekende gebruiker"))
        return full_name


class MetaObjectGroupSerializer(GroupSerializer):
    full_name = serializers.SerializerMethodField(
        help_text=_("User-friendly full name of group.")
    )

    class Meta:
        model = GroupSerializer.Meta.model
        fields = ("full_name", "name")

    def get_full_name(self, obj: Union[Dict, Group]) -> str:
        full_name = ""
        if isinstance(obj, Group):
            full_name = super().get_full_name(obj)
        else:
            full_name = obj.get("full_name", obj.get("name", "Onbekende groep"))
        return full_name


class MetaObjectUserSerializerSlugRelatedField(SerializerSlugRelatedField):
    response_serializer = MetaObjectUserSerializer


class MetaObjectGroupSerializerSlugRelatedField(SerializerSlugRelatedField):
    response_serializer = MetaObjectGroupSerializer
