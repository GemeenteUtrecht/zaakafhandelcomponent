import os
from copy import deepcopy
from unittest.mock import patch

from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.zaken import ZaakObject
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.core.models import CoreConfig
from zac.core.permissions import zaken_geforceerd_bijwerken, zaken_wijzigen
from zac.core.services import get_zaakobjecten
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

OBJECTS_ROOT = "https://objects.nl/api/v1/"
OBJECTTYPES_ROOT = "https://objecttypes.nl/api/v2/"
ZRC_ROOT = "https://zaken.nl/api/v1/"
CATALOGI_ROOT = "http://catalogus.nl/api/v1/"

OBJECT_1 = {
    "url": "https://objects.nl/api/v1/objects/aa44d251-0ddc-4bf2-b114-00a5ce1925d1",
    "uuid": "aa44d251-0ddc-4bf2-b114-00a5ce1925d1",
    "type": "https://objecttypes.nl/api/v2/objecttypes/4424fcca-e80b-462e-98ec-3bbd40748b44",
    "record": {
        "index": 1,
        "typeVersion": 9,
        "data": {
            "type": "Laadpaal",
            "adres": "asc",
            "status": "Laadpaal in ontwikkeling",
            "projectnummer": "wdqwd",
        },
        "startAt": "2021-02-16",
        "registrationAt": "2021-02-16",
    },
}

OBJECTTYPE_1 = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/4424fcca-e80b-462e-98ec-3bbd40748b44",
    "uuid": "4424fcca-e80b-462e-98ec-3bbd40748b44",
    "name": "Laadpaal uitbreiding",
    "namePlural": "Laadpalen uitbreiding",
    "description": "",
    "dataClassification": "open",
    "maintainerOrganization": "",
    "maintainerDepartment": "",
    "contactPerson": "",
    "contactEmail": "",
    "source": "",
    "updateFrequency": "unknown",
    "providerOrganization": "",
    "documentationUrl": "",
    "labels": {},
    "createdAt": "2021-02-10",
    "modifiedAt": "2021-02-16",
    "versions": [
        f"{OBJECTTYPES_ROOT}objecttypes/4424fcca-e80b-462e-98ec-3bbd40748b44/versions/1",
        f"{OBJECTTYPES_ROOT}objecttypes/4424fcca-e80b-462e-98ec-3bbd40748b44/versions/2",
    ],
}

OBJECT_2 = {
    "url": "https://objects.nl/api/v1/objects/a1bc0873-4337-432b-a0a1-a3436e05dc93",
    "uuid": "a1bc0873-4337-432b-a0a1-a3436e05dc93",
    "type": "https://objecttypes.nl/api/v2/objecttypes/ded177f2-f54f-4ec8-aa4c-22b571e002f1",
    "record": {
        "index": 1,
        "typeVersion": 1,
        "data": {
            "type": "Laadpaal",
            "adres": "Utrechtsestraat 40",
            "status": "Laadpaal in ontwikkeling",
            "objectid": 1,
        },
        "startAt": "2021-02-16",
        "registrationAt": "2021-02-16",
    },
}

OBJECTTYPE_2 = {
    "url": f"{OBJECTTYPES_ROOT}objecttypes/ded177f2-f54f-4ec8-aa4c-22b571e002f1",
    "uuid": "ded177f2-f54f-4ec8-aa4c-22b571e002f1",
    "name": "Laadpaal",
    "namePlural": "Laadpalen",
    "description": "",
    "dataClassification": "open",
    "maintainerOrganization": "",
    "maintainerDepartment": "",
    "contactPerson": "",
    "contactEmail": "",
    "source": "",
    "updateFrequency": "unknown",
    "providerOrganization": "",
    "documentationUrl": "",
    "labels": {},
    "createdAt": "2021-02-05",
    "modifiedAt": "2021-02-10",
    "versions": [
        f"{OBJECTTYPES_ROOT}objecttypes/ded177f2-f54f-4ec8-aa4c-22b571e002f1/versions/1",
    ],
}
ZAAK_OBJECT_URL = f"{ZRC_ROOT}zaakobjecten/5a52da0e-bd2b-4452-98a9-6144c1801fe5"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"


@requests_mock.Mocker()
class RelateObjectsToZaakTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.zrc_service = Service.objects.create(
            api_type=APITypes.zrc, api_root=ZRC_ROOT
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZRC_ROOT}zaken/1",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
        )

        cls.user = SuperUserFactory.create()
        cls.obj = deepcopy(OBJECT_1)
        cls.obj["type"] = OBJECTTYPE_1
        cls.fetch_object_patcher = patch(
            "zac.core.api.serializers.fetch_object", return_value=cls.obj
        )

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)
        self.fetch_object_patcher.start()
        self.addCleanup(self.fetch_object_patcher.stop)

    def test_create_object_relation(self, m):
        mock_service_oas_get(m, url=self.zrc_service.api_root, service="zrc")
        mock_resource_get(m, self.zaak)
        m.get(
            f"{ZRC_ROOT}zaakobjecten?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.post(
            f"{ZRC_ROOT}zaakobjecten",
            status_code=201,
            json={
                "url": f"{ZRC_ROOT}zaakobjecten/bcd3f232-2b6b-4830-95a2-b40bc1ee5a73",
                "uuid": "bcd3f232-2b6b-4830-95a2-b40bc1ee5a73",
                "zaak": self.zaak["url"],
                "object": f"{OBJECT_1['url']}",
                "objectType": "overige",
                "objectTypeOverige": "Laadpaal uitbreiding",
                "relatieomschrijving": "",
                "objectIdentificatie": {"overigeData": OBJECT_1["record"]["data"]},
            },
        )

        response = self.client.post(
            reverse(
                "zaakobject-create",
            ),
            data={
                "object": OBJECT_1["url"],
                "zaak": self.zaak["url"],
                "objectType": "overige",
                "objectTypeOverige": "Laadpaal uitbreiding",
                "objectIdentificatie": {"overigeData": OBJECT_1["record"]["data"]},
            },
        )

        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

    def test_create_object_relation_fail_not_unique(self, m):
        mock_service_oas_get(m, url=self.zrc_service.api_root, service="zrc")
        mock_resource_get(m, self.zaak)
        m.get(
            f"{ZRC_ROOT}zaakobjecten?zaak={self.zaak['url']}",
            json=paginated_response(
                [
                    {
                        "url": f"{ZRC_ROOT}zaakobjecten/bcd3f232-2b6b-4830-95a2-b40bc1ee5a73",
                        "uuid": "bcd3f232-2b6b-4830-95a2-b40bc1ee5a73",
                        "zaak": self.zaak["url"],
                        "object": f"{OBJECT_1['url']}",
                        "objectType": "overige",
                        "objectTypeOverige": "Laadpaal uitbreiding",
                        "relatieomschrijving": "",
                        "objectIdentificatie": {
                            "overigeData": OBJECT_1["record"]["data"]
                        },
                    }
                ]
            ),
        )

        response = self.client.post(
            reverse(
                "zaakobject-create",
            ),
            data={
                "object": OBJECT_1["url"],
                "zaak": self.zaak["url"],
            },
        )

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_create_object_relation_fail_afgestoten(self, m):
        mock_service_oas_get(m, url=self.zrc_service.api_root, service="zrc")
        mock_resource_get(m, self.zaak)
        m.get(
            f"{ZRC_ROOT}zaakobjecten?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        obj = deepcopy(OBJECT_1)
        obj["record"]["data"]["afgestoten"] = True
        obj["type"] = OBJECTTYPE_1

        with patch("zac.core.api.serializers.fetch_object", return_value=obj):
            response = self.client.post(
                reverse(
                    "zaakobject-create",
                ),
                data={
                    "object": OBJECT_1["url"],
                    "zaak": self.zaak["url"],
                },
            )

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "`{ot}` is `afgestoten`.".format(ot=OBJECTTYPE_1["name"]),
                }
            ],
        )

    def test_create_object_relation_cache_invalidation(self, m):
        mock_service_oas_get(m, url=self.zrc_service.api_root, service="zrc")
        mock_resource_get(m, self.zaak)
        m.get(
            f"{ZRC_ROOT}zaakobjecten?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.post(
            f"{ZRC_ROOT}zaakobjecten",
            status_code=201,
            json={
                "url": f"{ZRC_ROOT}zaakobjecten/bcd3f232-2b6b-4830-95a2-b40bc1ee5a73",
                "uuid": "bcd3f232-2b6b-4830-95a2-b40bc1ee5a73",
                "zaak": self.zaak["url"],
                "object": f"{OBJECT_1['url']}",
                "objectType": "overige",
                "objectTypeOverige": "Laadpaal uitbreiding",
                "relatieomschrijving": "",
                "objectIdentificatie": {"overigeData": OBJECT_1["record"]["data"]},
            },
        )
        self.assertEqual(m.call_count, 0)

        # call to populate cache
        get_zaakobjecten(factory(Zaak, self.zaak))
        self.assertEqual(
            m.call_count, 2
        )  # one request for schema, one for the actual request

        response = self.client.post(
            reverse(
                "zaakobject-create",
            ),
            data={
                "object": OBJECT_1["url"],
                "zaak": self.zaak["url"],
                "objectType": "overige",
                "objectTypeOverige": "Laadpaal uitbreiding",
                "objectIdentificatie": {"overigeData": OBJECT_1["record"]["data"]},
            },
        )
        self.assertEqual(
            m.call_count, 4
        )  # one get request for zaak, one post request for zaakobject

        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        # second get_zaakobjecten call should not hit the cache
        get_zaakobjecten(factory(Zaak, self.zaak))
        self.assertEqual(
            m.call_count, 5
        )  # one get request for zaak, one post request for zaakobject
        self.assertEqual(m.request_history[1].url, m.request_history[4].url)

    @patch.dict(os.environ, {"DEBUG": "False"})
    def test_create_object_relation_invalid_data(self, m):
        mock_service_oas_get(m, url=self.zrc_service.api_root, service="zrc")
        mock_resource_get(m, self.zaak)
        m.get(
            f"{ZRC_ROOT}zaakobjecten?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.post(
            f"{ZRC_ROOT}zaakobjecten", status_code=400, json={"detail": "some-detail"}
        )

        # Missing objectIdentificatie
        response = self.client.post(
            reverse(
                "zaakobject-create",
            ),
            data={
                "object": OBJECT_1["url"],
                "zaak": self.zaak["url"],
                "objectType": "overige",
                "objectTypeOverige": "Laadpaal uitbreiding",
            },
        )
        self.assertEqual(status.HTTP_500_INTERNAL_SERVER_ERROR, response.status_code)

    def test_delete_object_relation(self, m):
        zaak_object = generate_oas_component(
            "zrc", "schemas/ZaakObject", url=ZAAK_OBJECT_URL, zaak=self.zaak["url"]
        )
        zaak_object["objectIdentificatie"] = {}
        mock_service_oas_get(m, url=self.zrc_service.api_root, service="zrc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, zaak_object)
        m.delete(ZAAK_OBJECT_URL, status_code=204)

        url = f"{reverse('zaakobject-create')}?url={ZAAK_OBJECT_URL}"

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        last_request = m.request_history[-1]
        self.assertEqual(last_request.method, "DELETE")
        self.assertEqual(last_request.url, ZAAK_OBJECT_URL)

    def test_delete_object_relation_cache_invalidation(self, m):
        zaak_object = generate_oas_component(
            "zrc", "schemas/ZaakObject", url=ZAAK_OBJECT_URL, zaak=self.zaak["url"]
        )
        zaak_object["objectIdentificatie"] = {}
        mock_service_oas_get(m, url=self.zrc_service.api_root, service="zrc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, zaak_object)
        m.delete(ZAAK_OBJECT_URL, status_code=204)

        url = f"{reverse('zaakobject-create')}?url={ZAAK_OBJECT_URL}"

        m.get(
            f"{ZRC_ROOT}zaakobjecten?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        self.assertEqual(m.call_count, 0)

        # call to populate cache
        get_zaakobjecten(factory(Zaak, self.zaak))
        self.assertEqual(
            m.call_count, 2
        )  # one request for schema, one for the actual request

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(
            m.call_count, 5
        )  # one get request for fetch_zaakobject, one get request for get_zaak, one delete request for zaakobject

        self.assertEqual(m.request_history[-1].method, "DELETE")
        self.assertEqual(m.request_history[-1].url, ZAAK_OBJECT_URL)

        # second get_zaakobjecten call should not hit the cache
        get_zaakobjecten(factory(Zaak, self.zaak))
        self.assertEqual(
            m.call_count, 6
        )  # one get request for zaak, one post request for zaakobject
        self.assertEqual(m.request_history[1].url, m.request_history[5].url)


class RelateObjectsToZaakPermissionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.zrc, api_root=ZRC_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOME",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZRC_ROOT}zaken/1",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            startdatum="2020-12-25",
            uiterlijkeEinddatumAfdoening="2021-01-04",
        )

        cls.zaak_object = generate_oas_component(
            "zrc", "schemas/ZaakObject", url=ZAAK_OBJECT_URL, zaak=cls.zaak["url"]
        )
        cls.zaak_object["objectIdentificatie"] = {}

        cls.data = {
            "object": OBJECT_1["url"],
            "zaak": cls.zaak["url"],
            "objectType": "overige",
            "objectTypeOverige": "Laadpaal uitbreiding",
            "objectIdentificatie": {"overigeData": OBJECT_1["record"]["data"]},
        }
        cls.obj = deepcopy(OBJECT_1)
        cls.obj["type"] = OBJECTTYPE_1

    def test_not_authenticated(self):
        url = reverse("zaakobject-create")
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        url = f"{reverse('zaakobject-create')}?url={ZAAK_OBJECT_URL}"

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_other_permission(self, m, *mocks):
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{ZRC_ROOT}zaakobjecten?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)
        url = reverse("zaakobject-create")

        with patch("zac.core.api.serializers.fetch_object", return_value=self.obj):
            response = self.client.post(url, self.data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_has_perm(self, m, *mocks):
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{ZRC_ROOT}zaakobjecten?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.post(f"{ZRC_ROOT}zaakobjecten", status_code=201, json=self.zaak_object)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)
        url = reverse("zaakobject-create")

        with patch("zac.core.api.serializers.fetch_object", return_value=self.obj):
            response = self.client.post(url, self.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @requests_mock.Mocker()
    def test_create_has_perm_but_zaak_is_closed(self, m, *mocks):
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, {**self.zaak, "einddatum": "2020-01-01"})
        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{ZRC_ROOT}zaakobjecten?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.post(f"{ZRC_ROOT}zaakobjecten", status_code=201, json=self.zaak_object)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)
        url = reverse("zaakobject-create")

        with patch("zac.core.api.serializers.fetch_object", return_value=self.obj):
            response = self.client.post(url, self.data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_has_perm_also_for_closed_zaak(self, m, *mocks):
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, {**self.zaak, "einddatum": "2020-01-01"})
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{ZRC_ROOT}zaakobjecten?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.post(f"{ZRC_ROOT}zaakobjecten", status_code=201, json=self.zaak_object)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_geforceerd_bijwerken.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)
        url = reverse("zaakobject-create")

        with patch("zac.core.api.serializers.fetch_object", return_value=self.obj):
            response = self.client.post(url, self.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @requests_mock.Mocker()
    def test_delete_other_permisison(self, m):
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak_object)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)
        url = f"{reverse('zaakobject-create')}?url={ZAAK_OBJECT_URL}"

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_delete_has_perm(self, m):
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak_object)
        m.delete(ZAAK_OBJECT_URL, status_code=204)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)
        url = f"{reverse('zaakobject-create')}?url={ZAAK_OBJECT_URL}"

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @requests_mock.Mocker()
    def test_delete_has_perm_but_zaak_is_closed(self, m):
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, {**self.zaak, "einddatum": "2020-01-01"})
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak_object)
        m.delete(ZAAK_OBJECT_URL, status_code=204)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)
        url = f"{reverse('zaakobject-create')}?url={ZAAK_OBJECT_URL}"

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_delete_has_perm_also_for_closed_zaak(self, m):
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, {**self.zaak, "einddatum": "2020-01-01"})
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak_object)
        m.delete(ZAAK_OBJECT_URL, status_code=204)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_geforceerd_bijwerken.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)
        url = f"{reverse('zaakobject-create')}?url={ZAAK_OBJECT_URL}"

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


@requests_mock.Mocker()
class ZaakObjectTests(APITransactionTestCase):
    @patch(
        "zac.core.api.views.ZaakObjectsView.get_object",
    )
    @patch("zac.core.api.views.get_zaakobjecten")
    def test_relation_object_api(self, m, mock_get_zaakobjects, mock_zaak):
        user = SuperUserFactory.create()

        Service.objects.create(api_type=APITypes.zrc, api_root=ZRC_ROOT)
        object_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTS_ROOT
        )
        objecttype_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTTYPES_ROOT
        )

        config = CoreConfig.get_solo()
        config.primary_objects_api = object_service
        config.primary_objecttypes_api = objecttype_service
        config.save()

        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZRC_ROOT}zaken/1",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
        )
        zaakobject_1 = {
            "url": "http://zaken.nl/zaakobject/1",
            "zaak": zaak["url"],
            "object": OBJECT_1["url"],
            "object_type": "overige",
            "object_type_overige": "Laadpaal uitbreiding",
            "relatieomschrijving": "",
            "object_identificatie": None,
        }
        zaakobject_2 = {
            "url": "http://zaken.nl/zaakobject/2",
            "zaak": zaak["url"],
            "object": OBJECT_2["url"],
            "object_type": "overige",
            "object_type_overige": "Laadpaal",
            "relatieomschrijving": "",
            "object_identificatie": None,
        }

        mock_service_oas_get(m, url=object_service.api_root, service="objects")
        mock_service_oas_get(m, url=objecttype_service.api_root, service="objecttypes")

        mock_zaak.return_value = factory(Zaak, zaak)
        mock_get_zaakobjects.return_value = factory(
            ZaakObject, [zaakobject_1, zaakobject_2]
        )

        m.get(OBJECT_1["url"], json=OBJECT_1)
        m.get(OBJECT_2["url"], json=OBJECT_2)
        m.get(OBJECTTYPE_1["url"], json=OBJECTTYPE_1)
        m.get(
            f"{OBJECTTYPE_1['url']}/versions",
            json=[
                {"$id": "http://mock.example.com/mocked1"},
                {"$id": "http://mock.example.com/mocked2"},
            ],
        )
        m.get(OBJECTTYPE_2["url"], json=OBJECTTYPE_2)
        m.get(
            f"{OBJECTTYPE_2['url']}/versions",
            json=[
                {"$id": "http://mock.example.com/mocked3"},
            ],
        )
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([OBJECTTYPE_1, OBJECTTYPE_2]),
        )

        self.client.force_authenticate(user)

        response = self.client.get(
            reverse(
                "zaak-objects",
                kwargs={"bronorganisatie": "123456", "identificatie": "ZAAK-01"},
            )
        )
        self.assertEqual(200, response.status_code)

        object_groups = response.data

        self.assertTrue(isinstance(object_groups, list))

        for group in object_groups:
            item = group["items"][0]
            # Check that the items (the related objects) are dictionaries and not a string (URLs)
            self.assertTrue(isinstance(item, dict))
            zaakobject_url_mapping = {
                zaakobject["object"]: zaakobject["url"]
                for zaakobject in [zaakobject_1, zaakobject_2]
            }
            self.assertEqual(
                item["zaakobject_url"], zaakobject_url_mapping[item["url"]]
            )
