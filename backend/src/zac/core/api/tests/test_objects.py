from django.urls import reverse

import requests_mock
from furl import furl
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes

from zac.accounts.tests.factories import UserFactory
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response

OBJECTTYPES_ROOT = "http://objecttype.nl/api/v2/"
OBJECTS_ROOT = "http://object.nl/api/v1/"
CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"


@requests_mock.Mocker()
class ObjecttypesListTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.objecttypes_service = ServiceFactory.create(
            api_type=APITypes.orc, api_root=OBJECTTYPES_ROOT
        )

        cls.objecttype_1 = {
            "url": f"{OBJECTTYPES_ROOT}objecttypes/1",
            "name": "tree",
            "namePlural": "trees",
            "description": "",
            "data_classification": "",
            "maintainer_organization": "",
            "maintainer_department": "",
            "contact_person": "",
            "contact_email": "",
            "source": "",
            "update_frequency": "",
            "provider_organization": "",
            "documentation_url": "",
            "labels": {},
            "created_at": "2019-08-24",
            "modified_at": "2019-08-24",
            "versions": [],
        }
        cls.objecttype_2 = {
            "url": f"{OBJECTTYPES_ROOT}objecttypes/2",
            "name": "bin",
            "namePlural": "bins",
            "description": "",
            "data_classification": "",
            "maintainer_organization": "",
            "maintainer_department": "",
            "contact_person": "",
            "contact_email": "",
            "source": "",
            "update_frequency": "",
            "provider_organization": "",
            "documentation_url": "",
            "labels": {},
            "created_at": "2019-08-24",
            "modified_at": "2019-08-24",
            "versions": [],
        }

    def test_not_authenticated(self, m):
        list_url = reverse("objecttypes-list")
        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_objecttypes(self, m):
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([self.objecttype_1, self.objecttype_2]),
        )

        config = CoreConfig.get_solo()
        config.primary_objecttypes_api = self.objecttypes_service
        config.save()

        list_url = reverse("objecttypes-list")
        user = UserFactory.create()

        self.client.force_authenticate(user=user)
        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(2, len(response.json()))

    def test_retrieve_objecttypes_filter_meta_objects(self, m):
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([self.objecttype_1, self.objecttype_2]),
        )

        config = CoreConfig.get_solo()
        config.primary_objecttypes_api = self.objecttypes_service
        config.save()
        meta_config = MetaObjectTypesConfig.get_solo()
        meta_config.checklist_objecttype = self.objecttype_1["url"]
        meta_config.save()

        list_url = reverse("objecttypes-list")
        user = UserFactory.create()

        self.client.force_authenticate(user=user)
        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "url": "http://objecttype.nl/api/v2/objecttypes/2",
                    "name": "bin",
                    "namePlural": "bins",
                    "description": "",
                    "dataClassification": "",
                    "maintainerOrganization": "",
                    "maintainerDepartment": "",
                    "contactPerson": "",
                    "contactEmail": "",
                    "source": "",
                    "updateFrequency": "",
                    "providerOrganization": "",
                    "documentationUrl": "",
                    "labels": {},
                    "createdAt": "2019-08-24",
                    "modifiedAt": "2019-08-24",
                    "versions": [],
                }
            ],
        )

    def test_retrieve_objecttypes_filter_zaaktype(self, m):
        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            identificatie="ZT1",
            omschrijving="ZT1",
        )
        mock_resource_get(m, zaaktype)
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response(
                [
                    {
                        **self.objecttype_1,
                        "labels": {
                            "zaaktypeIdentificaties": [zaaktype["identificatie"]]
                        },
                    },
                    self.objecttype_2,
                ],
            ),
        )

        config = CoreConfig.get_solo()
        config.primary_objecttypes_api = self.objecttypes_service
        config.save()

        list_url = (
            furl(reverse("objecttypes-list")).set({"zaaktype": zaaktype["url"]}).url
        )
        user = UserFactory.create()

        self.client.force_authenticate(user=user)
        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "url": "http://objecttype.nl/api/v2/objecttypes/1",
                    "name": "tree",
                    "namePlural": "trees",
                    "description": "",
                    "dataClassification": "",
                    "maintainerOrganization": "",
                    "maintainerDepartment": "",
                    "contactPerson": "",
                    "contactEmail": "",
                    "source": "",
                    "updateFrequency": "",
                    "providerOrganization": "",
                    "documentationUrl": "",
                    "labels": {"zaaktypeIdentificaties": ["ZT1"]},
                    "createdAt": "2019-08-24",
                    "modifiedAt": "2019-08-24",
                    "versions": [],
                }
            ],
        )


@requests_mock.Mocker()
class ObjecttypeVersionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.objecttypes_service = ServiceFactory.create(
            api_type=APITypes.orc, api_root=OBJECTTYPES_ROOT
        )

        cls.objecttype_version = {
            "url": f"{OBJECTTYPES_ROOT}objecttypes/e0346ea0-75aa-47e0-9283-cfb35963b725/versions/0",
            "version": 0,
            "objectType": f"{OBJECTTYPES_ROOT}objecttypes/e0346ea0-75aa-47e0-9283-cfb35963b725",
            "status": "published",
            "jsonSchema": {
                "$id": "https://example.com/example.json",
                "type": "object",
                "title": "Wijk GU",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "default": {},
                "examples": [
                    {"REGIO_NUMMER": "0001", "GBWPCL_WIJK_OMSCHRIJVING": "West"}
                ],
                "required": ["REGIO_NUMMER", "GBWPCL_WIJK_OMSCHRIJVING"],
                "properties": {
                    "REGIO_NUMMER": {"type": "string", "description": "regio nummer"},
                    "GBWPCL_WIJK_OMSCHRIJVING": {
                        "type": "string",
                        "description": "SAPRRE wijk",
                    },
                },
                "description": "Een wijk van de gemeente Utrecht.",
            },
            "created_at": "2019-08-24",
            "modified_at": "2019-08-24",
            "published_at": "2019-08-24",
        }

    def test_not_authenticated(self, m):
        list_url = reverse(
            "objecttypesversion-read",
            kwargs={"uuid": "e0346ea0-75aa-47e0-9283-cfb35963b725", "version": "1"},
        )
        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_objecttype_version(self, m):
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes/e0346ea0-75aa-47e0-9283-cfb35963b725/versions/1",
            json=self.objecttype_version,
        )

        config = CoreConfig.get_solo()
        config.primary_objecttypes_api = self.objecttypes_service
        config.save()

        list_url = reverse(
            "objecttypesversion-read",
            kwargs={"uuid": "e0346ea0-75aa-47e0-9283-cfb35963b725", "version": "1"},
        )
        user = UserFactory.create()

        self.client.force_authenticate(user=user)
        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        result = response.json()

        self.assertEqual(0, result["version"])
        self.assertEqual(
            {
                "$id": "https://example.com/example.json",
                "type": "object",
                "title": "Wijk GU",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "default": {},
                "examples": [
                    {"REGIO_NUMMER": "0001", "GBWPCL_WIJK_OMSCHRIJVING": "West"}
                ],
                "required": ["REGIO_NUMMER", "GBWPCL_WIJK_OMSCHRIJVING"],
                "properties": {
                    "REGIO_NUMMER": {"type": "string", "description": "regio nummer"},
                    "GBWPCL_WIJK_OMSCHRIJVING": {
                        "type": "string",
                        "description": "SAPRRE wijk",
                    },
                },
                "description": "Een wijk van de gemeente Utrecht.",
            },
            result["jsonSchema"],
        )


@requests_mock.Mocker()
class ObjectSearchTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.objects_service = ServiceFactory.create(
            api_type=APITypes.orc, api_root=OBJECTS_ROOT
        )
        cls.objecttypes_service = ServiceFactory.create(
            api_type=APITypes.orc, api_root=OBJECTTYPES_ROOT
        )
        config = CoreConfig.get_solo()
        config.primary_objects_api = cls.objects_service
        config.primary_objecttypes_api = cls.objecttypes_service
        config.save()

        meta_config = MetaObjectTypesConfig.get_solo()
        meta_config.review_objecttype = f"{OBJECTTYPES_ROOT}objecttypes/12345"
        meta_config.save()

        cls.objecttype = {
            "url": f"{OBJECTTYPES_ROOT}objecttypes/1",
            "name": "Laadpaal",
            "namePlural": "Laadpalen",
            "description": "",
            "data_classification": "",
            "maintainer_organization": "",
            "maintainer_department": "",
            "contact_person": "",
            "contact_email": "",
            "source": "",
            "update_frequency": "",
            "provider_organization": "",
            "documentation_url": "",
            "labels": {
                "stringRepresentation": [
                    "field__type",
                    ", ",
                    "field__adres",
                    " - ",
                    "field__status",
                ]
            },
            "created_at": "2019-08-24",
            "modified_at": "2019-08-24",
            "versions": [],
        }

        cls.object = {
            "url": f"{OBJECTS_ROOT}objects/e0346ea0-75aa-47e0-9283-cfb35963b725",
            "type": cls.objecttype["url"],
            "record": {
                "index": 1,
                "typeVersion": 1,
                "data": {
                    "type": "Laadpaal",
                    "adres": "Utrechtsestraat 41",
                    "status": "In ontwikkeling",
                    "objectid": 2,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [5.114160150114911, 52.08850095597628],
                },
                "startAt": "2021-07-09",
                "endAt": None,
                "registrationAt": "2021-07-09",
                "correctionFor": None,
                "correctedBy": None,
            },
        }

    def test_not_authenticated(self, m):
        list_url = reverse("object-search")
        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_filter(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes", json=paginated_response([self.objecttype])
        )
        m.post(f"{OBJECTS_ROOT}objects/search", status_code=400)

        config = CoreConfig.get_solo()
        config.primary_objects_api = self.objects_service
        config.save()

        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        list_url = reverse("object-search")
        response = self.client.post(
            list_url, {"geometry": {"within": {"type": "Polygon", "coordinates": [[]]}}}
        )

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

    def test_filter(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes", json=paginated_response([self.objecttype])
        )
        m.post(f"{OBJECTS_ROOT}objects/search", json=paginated_response([self.object]))

        config = CoreConfig.get_solo()
        config.primary_objects_api = self.objects_service
        config.save()

        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        list_url = reverse("object-search")
        response = self.client.post(
            list_url,
            {
                "geometry": {
                    "within": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [5.040241219103334, 52.09434351690135],
                                [5.145297981798648, 52.13018632964422],
                                [5.196109749376771, 52.07409013759298],
                                [5.084873177111147, 52.0386246041859],
                                [5.040241219103334, 52.09434351690135],
                            ]
                        ],
                    }
                },
                "type": f"{OBJECTTYPES_ROOT}objecttypes/1",
                "data_attrs": "adres__exact__Utrechtsestraat 41",
                "date": "2021-07-19",
            },
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual(1, response.json()["count"])

        # Test that stringRepresentation is given
        self.assertEqual(
            response.json()["results"],
            [
                {
                    "url": "http://object.nl/api/v1/objects/e0346ea0-75aa-47e0-9283-cfb35963b725",
                    "type": f"{OBJECTTYPES_ROOT}objecttypes/1",
                    "record": {
                        "index": 1,
                        "typeVersion": 1,
                        "data": {
                            "type": "Laadpaal",
                            "adres": "Utrechtsestraat 41",
                            "status": "In ontwikkeling",
                            "objectid": 2,
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [5.114160150114911, 52.08850095597628],
                        },
                        "startAt": "2021-07-09",
                        "endAt": None,
                        "registrationAt": "2021-07-09",
                        "correctionFor": None,
                        "correctedBy": None,
                    },
                    "stringRepresentation": "Laadpaal, Utrechtsestraat 41 - In ontwikkeling",
                }
            ],
        )

    def test_filter_objecttype_not_found(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes", json=paginated_response([self.objecttype])
        )

        config = CoreConfig.get_solo()
        config.primary_objects_api = self.objects_service
        config.save()

        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        list_url = reverse("object-search")
        response = self.client.post(
            list_url,
            {
                "geometry": {
                    "within": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [5.040241219103334, 52.09434351690135],
                                [5.145297981798648, 52.13018632964422],
                                [5.196109749376771, 52.07409013759298],
                                [5.084873177111147, 52.0386246041859],
                                [5.040241219103334, 52.09434351690135],
                            ]
                        ],
                    }
                },
                "type": f"{OBJECTTYPES_ROOT}objecttypes/2",
                "data_attrs": "adres__exact__Utrechtsestraat 41",
                "date": "2021-07-19",
            },
        )

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "type",
                    "code": "invalid",
                    "reason": "OBJECTTYPE http://objecttype.nl/api/v2/objecttypes/2 not found.",
                }
            ],
        )

    def test_filter_objecttype_is_meta(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        ot2 = {
            "url": f"{OBJECTTYPES_ROOT}objecttypes/12345",
            "name": "Laadpaal",
            "namePlural": "Laadpalen",
            "description": "",
            "data_classification": "",
            "maintainer_organization": "",
            "maintainer_department": "",
            "contact_person": "",
            "contact_email": "",
            "source": "",
            "update_frequency": "",
            "provider_organization": "",
            "documentation_url": "",
            "labels": {
                "stringRepresentation": [
                    "field__type",
                    ", ",
                    "field__adres",
                    " - ",
                    "field__status",
                ]
            },
            "created_at": "2019-08-24",
            "modified_at": "2019-08-24",
            "versions": [],
        }
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([self.objecttype, ot2]),
        )

        config = CoreConfig.get_solo()
        config.primary_objects_api = self.objects_service
        config.save()

        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        list_url = reverse("object-search")
        response = self.client.post(
            list_url,
            {
                "geometry": {
                    "within": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [5.040241219103334, 52.09434351690135],
                                [5.145297981798648, 52.13018632964422],
                                [5.196109749376771, 52.07409013759298],
                                [5.084873177111147, 52.0386246041859],
                                [5.040241219103334, 52.09434351690135],
                            ]
                        ],
                    }
                },
                "type": ot2["url"],
                "data_attrs": "adres__exact__Utrechtsestraat 41",
                "date": "2021-07-19",
            },
        )

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "type",
                    "code": "invalid",
                    "reason": "OBJECTTYPE http://objecttype.nl/api/v2/objecttypes/12345 is a `meta`-objecttype.",
                }
            ],
        )
