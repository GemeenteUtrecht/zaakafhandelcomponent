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
    def for_user(self, user, actual: bool = False) -> models.QuerySet:
        qs = self.filter(auth_profiles__user=user).distinct()
        if actual:
            qs = qs.filter(
                models.Q(
                    auth_profiles__userauthorizationprofile__end__gte=timezone.now()
                )
                | models.Q(auth_profiles__userauthorizationprofile__end=None),
                auth_profiles__userauthorizationprofile__start__lte=timezone.now(),
            ).distinct()
        return qs

    def for_application(
        self, application_token, actual: bool = False
    ) -> models.QuerySet:
        qs = self.filter(auth_profiles__applicationtoken=application_token).distinct()
        if actual:
            qs = qs.filter(
                models.Q(
                    auth_profiles__applicationtokenauthorizationprofile__end__gte=timezone.now()
                )
                | models.Q(
                    auth_profiles__applicationtokenauthorizationprofile__end=None
                ),
                auth_profiles__applicationtokenauthorizationprofile__start__lte=timezone.now(),
            ).distinct()
        return qs

    def for_requester(self, request, actual: bool = False) -> models.QuerySet:
        if request.user:
            return self.for_user(request.user, actual=actual)

        return self.for_application(request.auth, actual=actual)
