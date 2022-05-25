from itertools import groupby
from typing import List, Optional

from django.db import models

from zac.accounts.models import User


class ChecklistAnswerQuerySet(models.QuerySet):
    def as_grouped_by_zaak(self, qs: models.QuerySet) -> List[dict]:
        """
        Checklist answers grouped by the zaak they belong to.

        """
        zaken = []
        for zaak_url, group in groupby(qs, key=lambda a: a.checklist.zaak):
            zaken.append({"zaak_url": zaak_url, "checklist_answers": list(group)})
        return zaken

    def as_werkvoorraad(
        self, user: Optional[User] = None, groups: Optional[models.QuerySet] = None
    ) -> List[dict]:
        """
        Retrieve the checklists answers for a given user.

        """
        if not user and not groups:
            qs = self.none()
            return qs

        if user:
            qs = self.filter(user_assignee=user, answer__exact="").order_by(
                "checklist__zaak", "created"
            )
            return self.as_grouped_by_zaak(qs)

        if groups:
            qs = self.filter(group_assignee__in=groups, answer__exact="").order_by(
                "checklist__zaak", "created"
            )
            return self.as_grouped_by_zaak(qs)
