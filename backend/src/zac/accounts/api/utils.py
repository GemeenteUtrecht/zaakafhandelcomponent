from itertools import groupby

from django.db import models


def group_permissions(permissions: models.QuerySet):
    groups = []
    for (role, object_type), permissions in groupby(
        permissions, key=lambda a: (a.role, a.object_type)
    ):
        groups.append(
            {
                "role": role,
                "object_type": object_type,
                "policies": [perm.policy for perm in permissions],
            }
        )
    return groups
