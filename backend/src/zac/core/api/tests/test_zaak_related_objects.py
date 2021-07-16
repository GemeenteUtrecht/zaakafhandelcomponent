from unittest.mock import patch

from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.zaken import ZaakObject
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import SuperUserFactory
from zac.core.models import CoreConfig
from zgw.models.zrc import Zaak

OBJECTS_ROOT = "https://objects.nl/api/v1/"
OBJECTTYPES_ROOT = "https://objecttypes.nl/api/v1/"
ZRC_ROOT = "https://zaken.nl/api/v1/"

OBJECT_1 = {
    "url": "https://objects.nl/api/v1/objects/aa44d251-0ddc-4bf2-b114-00a5ce1925d1",
    "uuid": "aa44d251-0ddc-4bf2-b114-00a5ce1925d1",
    "type": "https://objecttypes.nl/api/v1/objecttypes/4424fcca-e80b-462e-98ec-3bbd40748b44",
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
    "type": "https://objecttypes.nl/api/v1/objecttypes/ded177f2-f54f-4ec8-aa4c-22b571e002f1",
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


@requests_mock.Mocker()
class RelatedObjectsTests(APITransactionTestCase):
    """
    Test that related objects that live in the Objects API can be retrieved.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = SuperUserFactory.create()

        cls.zrc_service = Service.objects.create(
            api_type=APITypes.zrc, api_root=ZRC_ROOT
        )
        cls.object_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTS_ROOT
        )
        cls.objecttype_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTTYPES_ROOT
        )

        config = CoreConfig.get_solo()
        config.primary_objects_api = cls.object_service
        config.save()

        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZRC_ROOT}zaken/1",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
        )
        cls.zaakobject_1 = {
            "url": "http://zaken.nl/zaakobject/1",
            "zaak": cls.zaak["url"],
            "object": OBJECT_1["url"],
            "object_type": "overige",
            "object_type_overige": "Laadpaal uitbreiding",
            "relatieomschrijving": "",
            "object_identificatie": None,
        }
        cls.zaakobject_2 = {
            "url": "http://zaken.nl/zaakobject/2",
            "zaak": cls.zaak["url"],
            "object": OBJECT_2["url"],
            "object_type": "overige",
            "object_type_overige": "Laadpaal",
            "relatieomschrijving": "",
            "object_identificatie": None,
        }

    @patch(
        "zac.core.api.views.ZaakObjectsView.get_object",
    )
    @patch("zac.core.api.views.get_zaakobjecten")
    def test_relation_object_api(self, m, mock_get_zaakobjects, mock_zaak):
        mock_service_oas_get(m, url=self.object_service.api_root, service="objects")
        mock_service_oas_get(
            m, url=self.objecttype_service.api_root, service="objecttypes"
        )

        mock_zaak.return_value = factory(Zaak, self.zaak)
        mock_get_zaakobjects.return_value = factory(
            ZaakObject, [self.zaakobject_1, self.zaakobject_2]
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

        self.client.force_login(self.user)

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
            # Check that the items (the related objects) are dictionaries and not a string (URLs)
            self.assertTrue(isinstance(group["items"][0], dict))

    def test_create_object_relation(self, m):
        mock_service_oas_get(m, url=self.zrc_service.api_root, service="zrc")
        m.post(
            f"{ZRC_ROOT}zaakobjecten",
            status_code=201,
            json={
                "url": f"{ZRC_ROOT}zaakobjecten/bcd3f232-2b6b-4830-95a2-b40bc1ee5a73",
                "uuid": "bcd3f232-2b6b-4830-95a2-b40bc1ee5a73",
                "zaak": f"{self.zaak['url']}",
                "object": f"{OBJECT_1['url']}",
                "objectType": "overige",
                "objectTypeOverige": "Laadpaal uitbreiding",
                "relatieomschrijving": "",
                "objectIdentificatie": {"overigeData": OBJECT_1["record"]["data"]},
            },
        )

        self.client.force_login(self.user)

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

    def test_create_object_relation_invalid_data(self, m):
        self.client.force_login(self.user)

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

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        errors = response.json()

        self.assertIn("objectIdentificatie", errors)
