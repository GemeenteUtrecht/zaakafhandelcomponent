from itertools import groupby
from typing import List

from django.db import models


class AccessRequestQuerySet(models.QuerySet):
    def as_werkvoorraad(self, user) -> List[dict]:
        """
        Retrieve the access requests for current user

        Requests are grouped by the zaak
        """
        qs = self.filter(result="", handlers__in=[user]).order_by(
            "zaak", "requester__username"
        )

        zaken = []
        for zaak_url, group in groupby(qs, key=lambda a: a.zaak):
            zaken.append({"zaak_url": zaak_url, "requesters": list(group)})
        return zaken
