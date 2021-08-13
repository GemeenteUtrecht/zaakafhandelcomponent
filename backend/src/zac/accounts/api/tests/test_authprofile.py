from django.urls import reverse, reverse_lazy

from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from ...constants import PermissionObjectTypeChoices
from ...models import AuthorizationProfile, BlueprintPermission
from ...tests.factories import (
    AuthorizationProfileFactory,
    BlueprintPermissionFactory,
    RoleFactory,
    SuperUserFactory,
)

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d"


class AuthProfileAPITests(APITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.user = SuperUserFactory.create()
        self.client.force_authenticate(self.user)

    def test_list_auth_profiles(self):
        role1, role2 = RoleFactory.create_batch(2)
        blueprint_permission1 = BlueprintPermissionFactory.create(
            role=role1,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        blueprint_permission2 = BlueprintPermissionFactory.create(
            role=role1,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        blueprint_permission3 = BlueprintPermissionFactory.create(
            role=role2,
            object_type=PermissionObjectTypeChoices.document,
            policy={
                "catalogus": CATALOGUS_URL,
                "iotype_omschrijving": "DT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        auth_profile1, auth_profile2 = AuthorizationProfileFactory.create_batch(2)
        auth_profile1.blueprint_permissions.add(
            blueprint_permission1, blueprint_permission2
        )
        auth_profile2.blueprint_permissions.add(blueprint_permission3)
        url = reverse_lazy("authorizationprofile-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "url": f"http://testserver{reverse('authorizationprofile-detail', args=[auth_profile1.uuid])}",
                    "uuid": str(auth_profile1.uuid),
                    "name": auth_profile1.name,
                    "blueprintPermissions": [
                        {
                            "role": role1.name,
                            "objectType": PermissionObjectTypeChoices.zaak,
                            "policies": [
                                {
                                    "catalogus": CATALOGUS_URL,
                                    "zaaktypeOmschrijving": "ZT1",
                                    "maxVa": "zeer_geheim",
                                },
                                {
                                    "catalogus": CATALOGUS_URL,
                                    "zaaktypeOmschrijving": "ZT2",
                                    "maxVa": "openbaar",
                                },
                            ],
                        }
                    ],
                },
                {
                    "url": f"http://testserver{reverse('authorizationprofile-detail', args=[auth_profile2.uuid])}",
                    "uuid": str(auth_profile2.uuid),
                    "name": auth_profile2.name,
                    "blueprintPermissions": [
                        {
                            "role": role2.name,
                            "objectType": PermissionObjectTypeChoices.document,
                            "policies": [
                                {
                                    "catalogus": CATALOGUS_URL,
                                    "iotypeOmschrijving": "DT1",
                                    "maxVa": "openbaar",
                                }
                            ],
                        }
                    ],
                },
            ],
        )

    def test_retrieve_auth_profile(self):
        role1, role2 = RoleFactory.create_batch(2)
        blueprint_permission1 = BlueprintPermissionFactory.create(
            role=role1,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        blueprint_permission2 = BlueprintPermissionFactory.create(
            role=role1,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        blueprint_permission3 = BlueprintPermissionFactory.create(
            role=role2,
            object_type=PermissionObjectTypeChoices.document,
            policy={
                "catalogus": CATALOGUS_URL,
                "iotype_omschrijving": "DT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        auth_profile = AuthorizationProfileFactory.create()
        auth_profile.blueprint_permissions.add(
            blueprint_permission1, blueprint_permission2, blueprint_permission3
        )
        url = reverse("authorizationprofile-detail", args=[auth_profile.uuid])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "url": f"http://testserver{url}",
                "uuid": str(auth_profile.uuid),
                "name": auth_profile.name,
                "blueprintPermissions": [
                    {
                        "role": role1.name,
                        "objectType": PermissionObjectTypeChoices.zaak,
                        "policies": [
                            {
                                "catalogus": CATALOGUS_URL,
                                "zaaktypeOmschrijving": "ZT1",
                                "maxVa": "zeer_geheim",
                            },
                            {
                                "catalogus": CATALOGUS_URL,
                                "zaaktypeOmschrijving": "ZT2",
                                "maxVa": "openbaar",
                            },
                        ],
                    },
                    {
                        "role": role2.name,
                        "objectType": PermissionObjectTypeChoices.document,
                        "policies": [
                            {
                                "catalogus": CATALOGUS_URL,
                                "iotypeOmschrijving": "DT1",
                                "maxVa": "openbaar",
                            }
                        ],
                    },
                ],
            },
        )

    def test_create_auth_profile(self):
        role1, role2 = RoleFactory.create_batch(2)
        url = reverse_lazy("authorizationprofile-list")
        data = {
            "name": "some name",
            "blueprintPermissions": [
                {
                    "role": role1.name,
                    "objectType": PermissionObjectTypeChoices.zaak,
                    "policies": [
                        {
                            "catalogus": CATALOGUS_URL,
                            "zaaktypeOmschrijving": "ZT1",
                            "maxVa": "zeer_geheim",
                        },
                        {
                            "catalogus": CATALOGUS_URL,
                            "zaaktypeOmschrijving": "ZT2",
                            "maxVa": "openbaar",
                        },
                    ],
                },
                {
                    "role": role2.name,
                    "objectType": PermissionObjectTypeChoices.document,
                    "policies": [
                        {
                            "catalogus": CATALOGUS_URL,
                            "iotypeOmschrijving": "DT1",
                            "maxVa": "openbaar",
                        }
                    ],
                },
            ],
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AuthorizationProfile.objects.count(), 1)

        auth_profile = AuthorizationProfile.objects.get()

        self.assertEqual(auth_profile.name, "some name")
        self.assertEqual(auth_profile.blueprint_permissions.count(), 3)

        permission1, permission2, permission3 = list(
            auth_profile.blueprint_permissions.all()
        )
        self.assertEqual(permission1.role, role1)
        self.assertEqual(permission1.object_type, PermissionObjectTypeChoices.zaak)
        self.assertEqual(
            permission1.policy,
            {
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": "zeer_geheim",
            },
        )
        self.assertEqual(permission2.role, role1)
        self.assertEqual(permission2.object_type, PermissionObjectTypeChoices.zaak)
        self.assertEqual(
            permission2.policy,
            {
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT2",
                "max_va": "openbaar",
            },
        )
        self.assertEqual(permission3.role, role2)
        self.assertEqual(permission3.object_type, PermissionObjectTypeChoices.document)
        self.assertEqual(
            permission3.policy,
            {
                "catalogus": CATALOGUS_URL,
                "iotype_omschrijving": "DT1",
                "max_va": "openbaar",
            },
        )

    def test_create_auth_profile_reuse_existing_permissions(self):
        role1, role2 = RoleFactory.create_batch(2)
        blueprint_permission1 = BlueprintPermissionFactory.create(
            role=role1,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        blueprint_permission2 = BlueprintPermissionFactory.create(
            role=role1,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        blueprint_permission3 = BlueprintPermissionFactory.create(
            role=role2,
            object_type=PermissionObjectTypeChoices.document,
            policy={
                "catalogus": CATALOGUS_URL,
                "iotype_omschrijving": "DT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        url = reverse_lazy("authorizationprofile-list")
        data = {
            "name": "some name",
            "blueprintPermissions": [
                {
                    "role": role1.name,
                    "objectType": PermissionObjectTypeChoices.zaak,
                    "policies": [
                        {
                            "catalogus": CATALOGUS_URL,
                            "zaaktypeOmschrijving": "ZT1",
                            "maxVa": "zeer_geheim",
                        },
                        {
                            "catalogus": CATALOGUS_URL,
                            "zaaktypeOmschrijving": "ZT2",
                            "maxVa": "openbaar",
                        },
                    ],
                },
                {
                    "role": role2.name,
                    "objectType": PermissionObjectTypeChoices.document,
                    "policies": [
                        {
                            "catalogus": CATALOGUS_URL,
                            "iotypeOmschrijving": "DT1",
                            "maxVa": "openbaar",
                        }
                    ],
                },
            ],
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AuthorizationProfile.objects.count(), 1)

        auth_profile = AuthorizationProfile.objects.get()

        self.assertEqual(auth_profile.name, "some name")
        self.assertEqual(auth_profile.blueprint_permissions.count(), 3)
        self.assertEqual(BlueprintPermission.objects.count(), 3)

        for permission in [
            blueprint_permission1,
            blueprint_permission2,
            blueprint_permission3,
        ]:
            self.assertTrue(
                auth_profile.blueprint_permissions.filter(id=permission.id).exists()
            )

    def test_create_auth_profile_policy_incorrect_shape(self):
        role = RoleFactory.create()
        url = reverse_lazy("authorizationprofile-list")
        data = {
            "name": "some name",
            "blueprintPermissions": [
                {
                    "role": role.name,
                    "objectType": PermissionObjectTypeChoices.zaak,
                    "policies": [
                        {
                            "catalogus": CATALOGUS_URL,
                            "zaaktypeOmschrijving": "ZT1",
                        },
                    ],
                }
            ],
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "blueprintPermissions": [
                    {"policies": [{"maxVa": ["Dit veld is vereist."]}]}
                ]
            },
        )

    def test_update_auth_profile(self):
        role = RoleFactory.create()
        blueprint_permission = BlueprintPermissionFactory.create(
            role=role,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        auth_profile = AuthorizationProfileFactory.create()
        auth_profile.blueprint_permissions.add(blueprint_permission)
        url = reverse("authorizationprofile-detail", args=[auth_profile.uuid])
        data = {
            "name": auth_profile.name,
            "blueprintPermissions": [
                {
                    "role": role.name,
                    "objectType": PermissionObjectTypeChoices.zaak,
                    "policies": [
                        {
                            "catalogus": CATALOGUS_URL,
                            "zaaktypeOmschrijving": "ZT2",
                            "maxVa": "openbaar",
                        },
                    ],
                }
            ],
        }

        response = self.client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        auth_profile.refresh_from_db()

        self.assertEqual(auth_profile.blueprint_permissions.count(), 1)

        permission = auth_profile.blueprint_permissions.get()

        self.assertEqual(
            permission.policy,
            {
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT2",
                "max_va": "openbaar",
            },
        )
