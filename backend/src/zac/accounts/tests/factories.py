import factory
import factory.fuzzy

from ..constants import PermissionObjectType
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


class AuthorizationProfileFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("bs")

    class Meta:
        model = "accounts.AuthorizationProfile"


class AccessRequestFactory(factory.django.DjangoModelFactory):
    requester = factory.SubFactory(UserFactory)
    zaak = factory.Faker("url")

    class Meta:
        model = "accounts.AccessRequest"


class PermissionDefinitionFactory(factory.django.DjangoModelFactory):
    object_type = PermissionObjectType.zaak
    permission = factory.Faker("word")
    object_url = factory.Faker("url")

    class Meta:
        model = "accounts.PermissionDefinition"

    @factory.post_generation
    def for_user(obj, create, extracted, **kwargs):
        assert create, "PermissionDefinition must be saved in the DB"

        if extracted:
            extracted.permission_definitions.add(obj)


class BlueprintPermissionFactory(factory.django.DjangoModelFactory):
    object_type = PermissionObjectType.zaak
    permission = factory.Faker("word")
    policy = {"somefield": "somevalue"}

    class Meta:
        model = "accounts.BlueprintPermission"

    @factory.post_generation
    def for_user(obj, create, extracted, **kwargs):
        assert create, "BlueprintPermission must be saved in the DB"

        if extracted:
            auth_profile = AuthorizationProfileFactory.create()
            auth_profile.blueprint_permissions.add(obj)
            UserAuthorizationProfile.objects.create(
                user=extracted, auth_profile=auth_profile
            )
