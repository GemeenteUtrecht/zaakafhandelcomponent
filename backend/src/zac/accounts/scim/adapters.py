from django_scim.adapters import SCIMGroup, SCIMUser
from django_scim.constants import SchemaURI
from django_scim.exceptions import BadRequestError, NotImplementedError
from django_scim.utils import get_group_adapter, get_user_adapter

from zac.core.utils import build_absolute_url

from ..models import User


class AuthorizationProfileAdapter(SCIMGroup):
    id_field = "uuid"

    @property
    def location(self):
        return build_absolute_url(path=self.path, request=self.request)

    @property
    def members(self):
        users = User.objects.filter(userauthorizationprofile__auth_profile=self.obj)
        scim_users = [get_user_adapter()(user, self.request) for user in users]

        dicts = []
        for user in scim_users:
            d = {
                "value": user.id,
                "$ref": user.location,
                "display": user.display_name,
            }
            dicts.append(d)

        return dicts

    def to_dict(self):
        """
        Return a ``dict`` conforming to the SCIM Group Schema,
        ready for conversion to a JSON object.
        """
        return {
            "id": self.id,
            "schemas": [SchemaURI.GROUP],
            "displayName": self.display_name,
            "members": self.members,
            "meta": self.meta,
        }

    def handle_remove(self, path, value, operation):
        if path.first_path == ("members", None, None):
            members = value or []
            uuids = [member.get("value") for member in members]
            users = User.objects.filter(uuid__in=uuids)

            if len(uuids) != users.count():
                raise BadRequestError("Can not remove a non-existent user from group")

            for user in users:
                self.obj.user_set.remove(user)

        else:
            raise NotImplementedError


class UserAdapter(SCIMUser):
    id_field = "uuid"

    @property
    def location(self):
        return build_absolute_url(path=self.path, request=self.request)

    def delete(self):
        User.objects.filter(uuid=self.id).update(is_active=False)

    @property
    def groups(self):
        """
        Return the groups of the user per the SCIM spec.
        """
        groups = self.obj.auth_profiles.all()
        scim_groups = [get_group_adapter()(group, self.request) for group in groups]

        dicts = []
        for group in scim_groups:
            d = {
                "value": group.id,
                "$ref": group.location,
                "display": group.display_name,
            }
            dicts.append(d)

        return dicts

    def to_dict(self):
        """
        Return a ``dict`` conforming to the SCIM User Schema,
        ready for conversion to a JSON object.
        """
        return {
            "id": self.id,
            "schemas": [SchemaURI.USER],
            "userName": self.obj.username,
            "name": {
                "givenName": self.obj.first_name,
                "familyName": self.obj.last_name,
                "formatted": self.name_formatted,
            },
            "displayName": self.display_name,
            "emails": self.emails,
            "active": self.obj.is_active,
            "groups": self.groups,
            "meta": self.meta,
        }
