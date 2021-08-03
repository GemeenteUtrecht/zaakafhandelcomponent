from django_scim.adapters import SCIMGroup, SCIMUser
from django_scim.constants import SchemaURI
from django_scim.utils import get_user_adapter

from zac.core.utils import build_absolute_url

from .models import User


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


class UserAdapter(SCIMUser):
    id_field = "username"

    @property
    def location(self):
        return build_absolute_url(path=self.path, request=self.request)
