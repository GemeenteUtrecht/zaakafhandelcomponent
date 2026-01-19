from itertools import groupby
from typing import List, Optional

from django.contrib.auth.models import Group
from django.db import models

from zac.accounts.models import User

from .constants import ActivityStatuses


class ActivityQuerySet(models.QuerySet):
    def as_grouped_by_zaak(self, qs: models.QuerySet) -> List[dict]:
        """
        Activities grouped by the zaak they belong to.

        """
        zaken = []
        for zaak_url, group in groupby(qs, key=lambda a: a.zaak):
            zaken.append({"zaak_url": zaak_url, "activities": list(group)})
        return zaken

    def as_werkvoorraad(
        self, user: Optional[User] = None, groups: Optional[models.QuerySet] = None
    ) -> List[dict]:
        """
        Retrieve the on-going activities for a given user.

        """
        if not user and not groups:
            qs = self.none()
            return qs

        if user:
            qs = self.filter(
                status=ActivityStatuses.on_going, user_assignee=user
            ).order_by("zaak", "created")
            return self.as_grouped_by_zaak(qs)

        if groups:
            qs = self.filter(
                status=ActivityStatuses.on_going, group_assignee__in=groups
            ).order_by("zaak", "created")
            return self.as_grouped_by_zaak(qs)
