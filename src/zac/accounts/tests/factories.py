import factory
import factory.fuzzy

from ..models import UserAuthorizationProfile


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.Sequence(lambda n: f"user-{n}@zac")

    class Meta:
        model = "accounts.User"


class StaffUserFactory(UserFactory):
    is_staff = True


class SuperUserFactory(StaffUserFactory):
    is_superuser = True


class PermissionSetFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f"perms-{n}")
    catalogus = factory.Faker("url")

    class Meta:
        model = "accounts.PermissionSet"

    @factory.post_generation
    def for_user(obj, create, extracted, **kwargs):
        assert create, "PermissionSet must be saved in the DB"

        auth_profile = AuthorizationProfileFactory.create()
        auth_profile.permission_sets.add(obj)
        UserAuthorizationProfile.objects.create(
            user=extracted, auth_profile=auth_profile
        )


class AuthorizationProfileFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("bs")

    class Meta:
        model = "accounts.AuthorizationProfile"


class AccessRequestFactory(factory.django.DjangoModelFactory):
    requester = factory.SubFactory(UserFactory)
    zaak = factory.Faker("url")
    handler = factory.SubFactory(UserFactory)

    class Meta:
        model = "accounts.AccessRequest"
