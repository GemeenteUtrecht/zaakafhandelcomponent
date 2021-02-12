from datetime import date

from django.db import models


class AccessRequestQuerySet(models.QuerySet):
    def actual(self) -> models.QuerySet:
        return self.filter(
            models.Q(end_date__gte=date.today()) | models.Q(end_date=None)
        )
