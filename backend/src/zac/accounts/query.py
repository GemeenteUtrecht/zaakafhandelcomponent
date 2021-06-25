from django.db import models
from django.utils import timezone


class AccessRequestQuerySet(models.QuerySet):
    def actual(self) -> models.QuerySet:
        return self.filter(handled_date=None)


class AtomicPermissionQuerySet(models.QuerySet):
    def for_user(self, user) -> models.QuerySet:
        return self.filter(users=user).distinct()


class UserAtomicPermissionQuerySet(models.QuerySet):
    def actual(self) -> models.QuerySet:
        return self.filter(
            models.Q(end_date__gte=timezone.now()) | models.Q(end_date=None),
            start_date__lte=timezone.now(),
        )


class BlueprintPermissionQuerySet(models.QuerySet):
    def for_user(self, user) -> models.QuerySet:
        return self.filter(auth_profiles__user=user).distinct()

    def actual(self) -> models.QuerySet:
        return self.filter(
            models.Q(end_date__gte=timezone.now()) | models.Q(end_date=None),
            start_date__lte=timezone.now(),
        )
