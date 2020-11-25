from itertools import groupby
from typing import List

from django.db import models

from zac.accounts.models import User

from .constants import ActivityStatuses


class ActivityQuerySet(models.QuerySet):
    def as_werkvoorraad(self, user: User) -> List[dict]:
        """
        Retrieve the on-going activities for a given user

        Activities are grouped by the zaak they belong too.
        """
        qs = self.filter(status=ActivityStatuses.on_going, assignee=user).order_by(
            "zaak", "created"
        )

        zaken = []
        for zaak_url, group in groupby(qs, key=lambda a: a.zaak):
            zaken.append({"zaak_url": zaak_url, "activities": list(group)})
        return zaken
