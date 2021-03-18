import factory
import factory.fuzzy
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from ..constants import PermissionObjectType
from ..models import InformatieobjecttypePermission, UserAuthorizationProfile


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


class InformatieobjecttypePermissionFactory(factory.django.DjangoModelFactory):
    permission_set = factory.SubFactory(PermissionSetFactory)
    catalogus = factory.Faker("url")
    max_va = VertrouwelijkheidsAanduidingen.openbaar

    class Meta:
        model = InformatieobjecttypePermission


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
