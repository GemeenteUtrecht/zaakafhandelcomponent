from django.urls import reverse, reverse_lazy

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes

from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response

from ...constants import PermissionObjectTypeChoices
from ...models import AuthorizationProfile, BlueprintPermission
from ...tests.factories import (
    AuthorizationProfileFactory,
    BlueprintPermissionFactory,
    RoleFactory,
    StaffUserFactory,
    SuperUserFactory,
    UserFactory,
)

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d"


class AuthProfilePermissionsTests(APITestCase):
    url = reverse_lazy("authorizationprofile-list")

    def test_no_staff_user(self):
        user = UserFactory.create()
        self.client.force_authenticate(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user(self):
        user = StaffUserFactory.create()
        self.client.force_authenticate(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser(self):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AuthProfileAPITests(ClearCachesMixin, APITransactionTestCase):
    catalogus = generate_oas_component(
        "ztc",
        "schemas/Catalogus",
        url=CATALOGUS_URL,
        domein="DOME",
    )
    zaaktype1 = generate_oas_component(
        "ztc",
        "schemas/ZaakType",
        url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
        identificatie="ZT1",
        catalogus=CATALOGUS_URL,
        omschrijving="ZT1",
        informatieobjecttypen=[],
    )
    zaaktype2 = generate_oas_component(
        "ztc",
        "schemas/ZaakType",
        url=f"{CATALOGI_ROOT}zaaktypen/cb7ae15e-6260-4373-b6dc-e334fedb8be9",
        identificatie="ZT2",
        catalogus=CATALOGUS_URL,
        omschrijving="ZT2",
        informatieobjecttypen=[],
    )
    iotype = generate_oas_component(
        "ztc",
        "schemas/InformatieObjectType",
        url=f"{CATALOGI_ROOT}informatieobjecttypen/2f4c1d80-764c-45f9-95c9-32816b26a436",
        omschrijving="IOT2",
        catalogus=CATALOGUS_URL,
        vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
    )
    ziot1 = generate_oas_component(
        "ztc",
        "schemas/ZaakTypeInformatieObjectType",
        zaaktype=zaaktype1["url"],
        informatieobjecttype=iotype["url"],
    )
    ziot2 = generate_oas_component(
        "ztc",
        "schemas/ZaakTypeInformatieObjectType",
        zaaktype=zaaktype2["url"],
        informatieobjecttype=iotype["url"],
    )

    def setUp(self) -> None:
        super().setUp()

        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        self.user = SuperUserFactory.create()
        self.client.force_authenticate(self.user)

    def test_list_auth_profiles(self):
        role1, role2 = RoleFactory.create_batch(2)
        blueprint_permission1 = BlueprintPermissionFactory.create(
            role=role1,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        blueprint_permission2 = BlueprintPermissionFactory.create(
            role=role1,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        blueprint_permission3 = BlueprintPermissionFactory.create(
            role=role2,
            object_type=PermissionObjectTypeChoices.document,
            policy={
                "catalogus": "DOME",
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
                            "role": role1.id,
                            "objectType": PermissionObjectTypeChoices.zaak,
                            "policies": [
                                {
                                    "catalogus": "DOME",
                                    "zaaktypeOmschrijving": "ZT1",
                                    "maxVa": "zeer_geheim",
                                },
                                {
                                    "catalogus": "DOME",
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
                            "role": role2.id,
                            "objectType": PermissionObjectTypeChoices.document,
                            "policies": [
                                {
                                    "catalogus": "DOME",
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
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        blueprint_permission2 = BlueprintPermissionFactory.create(
            role=role1,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        blueprint_permission3 = BlueprintPermissionFactory.create(
            role=role2,
            object_type=PermissionObjectTypeChoices.document,
            policy={
                "catalogus": "DOME",
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
                        "role": role1.id,
                        "objectType": PermissionObjectTypeChoices.zaak,
                        "policies": [
                            {
                                "catalogus": "DOME",
                                "zaaktypeOmschrijving": "ZT1",
                                "maxVa": "zeer_geheim",
                            },
                            {
                                "catalogus": "DOME",
                                "zaaktypeOmschrijving": "ZT2",
                                "maxVa": "openbaar",
                            },
                        ],
                    },
                    {
                        "role": role2.id,
                        "objectType": PermissionObjectTypeChoices.document,
                        "policies": [
                            {
                                "catalogus": "DOME",
                                "iotypeOmschrijving": "DT1",
                                "maxVa": "openbaar",
                            }
                        ],
                    },
                ],
            },
        )

    @requests_mock.Mocker()
    def test_create_auth_profile(self, m):
        # setup mocks
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(f"{CATALOGI_ROOT}catalogussen", json=paginated_response([self.catalogus]))
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([self.zaaktype1, self.zaaktype2]),
        )
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen?zaaktype={self.zaaktype1['url']}",
            json=paginated_response([self.ziot1]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen?zaaktype={self.zaaktype2['url']}",
            json=paginated_response([self.ziot2]),
        )
        mock_resource_get(m, self.iotype)

        role1, role2 = RoleFactory.create_batch(2)
        url = reverse_lazy("authorizationprofile-list")
        data = {
            "name": "some name",
            "blueprintPermissions": [
                {
                    "role": role1.id,
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
                    "role": role2.id,
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
        self.assertEqual(auth_profile.blueprint_permissions.count(), 5)

        permission1, permission2 = list(
            auth_profile.blueprint_permissions.filter(
                object_type=PermissionObjectTypeChoices.zaak
            )
        )
        self.assertEqual(permission1.role, role1)
        self.assertEqual(permission1.object_type, PermissionObjectTypeChoices.zaak)
        self.assertEqual(
            permission1.policy,
            {
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": "zeer_geheim",
            },
        )
        self.assertEqual(permission2.role, role1)
        self.assertEqual(permission2.object_type, PermissionObjectTypeChoices.zaak)
        self.assertEqual(
            permission2.policy,
            {
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT2",
                "max_va": "openbaar",
            },
        )

        permission1, permission2, permission3 = list(
            auth_profile.blueprint_permissions.filter(
                object_type=PermissionObjectTypeChoices.document
            )
        )
        self.assertEqual(permission1.role, role1)
        self.assertEqual(permission1.object_type, PermissionObjectTypeChoices.document)
        self.assertEqual(
            permission1.policy,
            {
                "catalogus": "DOME",
                "iotype_omschrijving": "IOT2",
                "max_va": "zeer_geheim",
            },
        )
        self.assertEqual(permission2.role, role1)
        self.assertEqual(permission2.object_type, PermissionObjectTypeChoices.document)
        self.assertEqual(
            permission2.policy,
            {
                "catalogus": "DOME",
                "iotype_omschrijving": "IOT2",
                "max_va": "openbaar",
            },
        )
        self.assertEqual(permission3.role, role2)
        self.assertEqual(permission3.object_type, PermissionObjectTypeChoices.document)
        self.assertEqual(
            permission3.policy,
            {
                "catalogus": "DOME",
                "iotype_omschrijving": "DT1",
                "max_va": "openbaar",
            },
        )

    @requests_mock.Mocker()
    def test_create_auth_profile_reuse_existing_permissions(self, m):
        # setup mocks
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(f"{CATALOGI_ROOT}catalogussen", json=paginated_response([self.catalogus]))
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([self.zaaktype1, self.zaaktype2]),
        )
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen?zaaktype={self.zaaktype1['url']}",
            json=paginated_response([self.ziot1]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen?zaaktype={self.zaaktype2['url']}",
            json=paginated_response([self.ziot2]),
        )
        mock_resource_get(m, self.iotype)

        role1, role2 = RoleFactory.create_batch(2)
        blueprint_permission1 = BlueprintPermissionFactory.create(
            role=role1,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        blueprint_permission2 = BlueprintPermissionFactory.create(
            role=role1,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        blueprint_permission3 = BlueprintPermissionFactory.create(
            role=role2,
            object_type=PermissionObjectTypeChoices.document,
            policy={
                "catalogus": "DOME",
                "iotype_omschrijving": "DT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        url = reverse_lazy("authorizationprofile-list")
        data = {
            "name": "some name",
            "blueprintPermissions": [
                {
                    "role": role1.id,
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
                    "role": role2.id,
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
        self.assertEqual(BlueprintPermission.objects.count(), 3)

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AuthorizationProfile.objects.count(), 1)

        auth_profile = AuthorizationProfile.objects.get()

        self.assertEqual(auth_profile.name, "some name")
        self.assertEqual(auth_profile.blueprint_permissions.count(), 5)
        self.assertEqual(BlueprintPermission.objects.count(), 5)

    def test_create_auth_profile_policy_incorrect_shape(self):
        role = RoleFactory.create()
        url = reverse_lazy("authorizationprofile-list")
        data = {
            "name": "some name",
            "blueprintPermissions": [
                {
                    "role": role.id,
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
            response.json()["invalidParams"],
            [
                {
                    "code": "required",
                    "name": "blueprintPermissions.0.policies.0.maxVa",
                    "reason": "Dit veld is vereist.",
                }
            ],
        )

    @requests_mock.Mocker()
    def test_update_auth_profile(self, m):
        # setup mocks
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(f"{CATALOGI_ROOT}catalogussen", json=paginated_response([self.catalogus]))
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([self.zaaktype1, self.zaaktype2]),
        )
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen?zaaktype={self.zaaktype1['url']}",
            json=paginated_response([self.ziot1]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen?zaaktype={self.zaaktype2['url']}",
            json=paginated_response([self.ziot2]),
        )
        mock_resource_get(m, self.iotype)

        role = RoleFactory.create()
        blueprint_permission = BlueprintPermissionFactory.create(
            role=role,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": "DOME",
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
                    "role": role.id,
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
        self.assertEqual(auth_profile.blueprint_permissions.count(), 2)

        permission = auth_profile.blueprint_permissions.filter(
            object_type=PermissionObjectTypeChoices.zaak
        )
        self.assertEqual(
            permission[0].policy,
            {
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT2",
                "max_va": "openbaar",
            },
        )

        permission = auth_profile.blueprint_permissions.filter(
            object_type=PermissionObjectTypeChoices.document
        )
        self.assertEqual(
            permission[0].policy,
            {
                "catalogus": "DOME",
                "iotype_omschrijving": "IOT2",
                "max_va": "openbaar",
            },
        )

    def test_delete_auth_profile(self):
        role1, role2 = RoleFactory.create_batch(2)
        blueprint_permission1 = BlueprintPermissionFactory.create(
            role=role1,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        blueprint_permission2 = BlueprintPermissionFactory.create(
            role=role1,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        blueprint_permission3 = BlueprintPermissionFactory.create(
            role=role2,
            object_type=PermissionObjectTypeChoices.document,
            policy={
                "catalogus": "DOME",
                "iotype_omschrijving": "DT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        auth_profile = AuthorizationProfileFactory.create()
        auth_profile.blueprint_permissions.add(
            blueprint_permission1, blueprint_permission2, blueprint_permission3
        )
        url = reverse("authorizationprofile-detail", args=[auth_profile.uuid])

        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
