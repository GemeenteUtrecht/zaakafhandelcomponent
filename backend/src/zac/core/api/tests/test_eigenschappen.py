from re import M
from unittest.mock import patch

from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes

from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"


@requests_mock.Mocker()
@patch(
    "zac.core.api.views.fetch_zaaktypeattributen_objects_for_zaaktype", return_value=[]
)
class EigenschappenPermissionTests(ClearCachesMixin, APITransactionTestCase):
    catalogus = generate_oas_component(
        "ztc",
        "schemas/Catalogus",
        url=CATALOGUS_URL,
        domein="DOME",
    )
    zaaktype = generate_oas_component(
        "ztc",
        "schemas/ZaakType",
        url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
        identificatie="ZT1",
        catalogus=CATALOGUS_URL,
        vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        omschrijving="ZT1",
    )
    eigenschap = generate_oas_component(
        "ztc",
        "schemas/Eigenschap",
        zaaktype=zaaktype["url"],
        naam="some-property",
        specificatie={
            "groep": "dummy",
            "formaat": "tekst",
            "lengte": "3",
            "kardinaliteit": "1",
            "waardenverzameling": [],
        },
    )
    endpoint = reverse("eigenschappen")

    def setUp(self):
        super().setUp()
        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

    def test_not_authenticated(self, m, *mocks):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([self.zaaktype]),
        )

        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_identificatie": "ZT1"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 0)

        mock_resource_get(m, self.zaaktype)
        response = self.client.get(self.endpoint, {"zaaktype": self.zaaktype["url"]})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 0)

    def test_has_perm_but_not_for_zaaktype(self, m, *mocks):
        zaaktype2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/741c9d1e-de1c-46c6-9ae0-5696f7994ab6",
            identificatie="ZT2",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT2",
        )

        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([self.zaaktype, zaaktype2]),
        )
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_identificatie": "ZT1"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 0)

        mock_resource_get(m, self.zaaktype)
        response = self.client.get(self.endpoint, {"zaaktype": self.zaaktype["url"]})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 0)

    def test_is_superuser(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.eigenschap]),
        )
        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_identificatie": "ZT1"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)

        mock_resource_get(m, self.zaaktype)
        response = self.client.get(self.endpoint, {"zaaktype": self.zaaktype["url"]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_has_perms(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.eigenschap]),
        )
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_identificatie": "ZT1"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data), 1)

        mock_resource_get(m, self.zaaktype)
        response = self.client.get(self.endpoint, {"zaaktype": self.zaaktype["url"]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)


class EigenschappenResponseTests(ClearCachesMixin, APITransactionTestCase):
    endpoint = reverse("eigenschappen")

    def setUp(self):
        super().setUp()

        # ensure that we have a user with all permissions
        self.user = SuperUserFactory.create()
        self.client.force_authenticate(user=self.user)
        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

    @patch(
        "zac.core.api.views.fetch_zaaktypeattributen_objects_for_zaaktype",
        return_value=[],
    )
    @requests_mock.Mocker()
    def test_get_eigenschappen_string(self, mock_fetch_ztao, m):
        zaaktype1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        eigenschap1 = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype1["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": ["aaa", "bbb"],
            },
        )
        zaaktype2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/741c9d1e-de1c-46c6-9ae0-5696f7994ab6",
            identificatie="ZT2",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT2",
        )
        eigenschap2 = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype1["url"],
            naam="other-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "255",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )

        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, zaaktype1)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([zaaktype1, zaaktype2]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={zaaktype1['url']}",
            json=paginated_response([eigenschap1, eigenschap2]),
        )

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_identificatie": "ZT1"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(
            data,
            [
                {
                    "name": "other-property",
                    "spec": {
                        "type": "string",
                        "format": "long",
                        "minLength": 1,
                        "maxLength": 255,
                    },
                },
                {
                    "name": "some-property",
                    "spec": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 3,
                        "enum": [
                            {"label": "aaa", "value": "aaa"},
                            {"label": "bbb", "value": "bbb"},
                        ],
                    },
                },
            ],
        )

    @patch(
        "zac.core.api.views.fetch_zaaktypeattributen_objects_for_zaaktype",
        return_value=[],
    )
    @requests_mock.Mocker()
    def test_get_eigenschappen_number(self, mock_fetch_ztao, m):
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "getal",
                "lengte": "1",
                "kardinaliteit": "1",
                "waardenverzameling": [1.0, 2],
            },
        )

        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, zaaktype)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([zaaktype]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={zaaktype['url']}",
            json=paginated_response([eigenschap]),
        )

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_identificatie": "ZT1"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            [
                {
                    "name": "some-property",
                    "spec": {
                        "type": "number",
                        "enum": [
                            {"label": "1.0", "value": 1.0},
                            {"label": "2", "value": 2},
                        ],
                    },
                }
            ],
        )

    @patch(
        "zac.core.api.views.fetch_zaaktypeattributen_objects_for_zaaktype",
        return_value=[],
    )
    def test_get_eigenschappen_with_all_query_params(self, mock_fetch_ztao):
        response = self.client.get(
            self.endpoint,
            {
                "catalogus": "some-url",
                "zaaktype_identificatie": "ZT1",
                "zaaktype": "some-zaaktype",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "zaaktype",
                    "code": "invalid",
                    "reason": "Voer een geldige URL in.",
                },
                {
                    "name": "catalogus",
                    "code": "invalid",
                    "reason": "Voer een geldige URL in.",
                },
            ],
        )

    @patch(
        "zac.core.api.views.fetch_zaaktypeattributen_objects_for_zaaktype",
        return_value=[],
    )
    def test_get_eigenschappen_without_query_params(self, mock_fetch_ztao):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "De CATALOGUS en `zaaktype_identificatie` zijn beide vereist als 1 is opgegeven.",
                }
            ],
        )

    @patch(
        "zac.core.api.views.fetch_zaaktypeattributen_objects_for_zaaktype",
        return_value=[],
    )
    def test_get_eigenschappen_with_invalid_query_param(self, mock_fetch_ztao):
        response = self.client.get(
            self.endpoint, {"catalogus": "some-url", "zaaktype_identificatie": "ZT1"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "catalogus",
                    "code": "invalid",
                    "reason": "Voer een geldige URL in.",
                }
            ],
        )

        response = self.client.get(self.endpoint, {"zaaktype": "some-url"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "code": "invalid",
                    "name": "zaaktype",
                    "reason": "Voer een geldige URL in.",
                }
            ],
        )

    @patch(
        "zac.core.api.views.fetch_zaaktypeattributen_objects_for_zaaktype",
        return_value=[],
    )
    @requests_mock.Mocker()
    def test_get_eigenschappen_with_same_name_and_spec(self, mock_fetch_ztao, m):
        zaaktype1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT",
        )
        eigenschap1 = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype1["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": ["aaa", "bbb"],
            },
        )
        zaaktype2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/741c9d1e-de1c-46c6-9ae0-5696f7994ab6",
            identificatie="ZT",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT",
        )
        eigenschap2 = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype2["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": ["aaa", "bbb"],
            },
        )

        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, zaaktype1)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([zaaktype1, zaaktype2]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={zaaktype1['url']}",
            json=paginated_response([eigenschap1]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={zaaktype2['url']}",
            json=paginated_response([eigenschap2]),
        )

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_identificatie": "ZT"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            [
                {
                    "name": "some-property",
                    "spec": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 3,
                        "enum": [
                            {"label": "aaa", "value": "aaa"},
                            {"label": "bbb", "value": "bbb"},
                        ],
                    },
                }
            ],
        )

    @patch(
        "zac.core.api.views.fetch_zaaktypeattributen_objects_for_zaaktype",
        return_value=[],
    )
    @patch("zac.core.services.logger")
    @requests_mock.Mocker()
    def test_get_eigenschappen_with_same_name_but_different_spec(
        self, m_logger, mock_ztao, m_req
    ):
        zaaktype1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT",
        )
        eigenschap1 = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype1["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": ["aaa", "bbb"],
            },
        )
        zaaktype2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/741c9d1e-de1c-46c6-9ae0-5696f7994ab6",
            identificatie="ZT",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT",
        )
        eigenschap2 = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype2["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "1",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )

        mock_service_oas_get(m_req, CATALOGI_ROOT, "ztc")
        mock_resource_get(m_req, zaaktype1)
        m_req.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([zaaktype1, zaaktype2]),
        )
        m_req.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={zaaktype1['url']}",
            json=paginated_response([eigenschap1]),
        )
        m_req.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={zaaktype2['url']}",
            json=paginated_response([eigenschap2]),
        )

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_identificatie": "ZT"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)
        # can't assert spec since it's value is uncertain
        self.assertEqual(data[0]["name"], "some-property")
        m_logger.warning.assert_called_with(
            "Eigenschappen 'some-property' which belong to zaaktype 'ZT' have different specs"
        )

    @requests_mock.Mocker()
    def test_get_eigenschappen_specification_from_objects(self, m):
        catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOMEIN",
        )
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "getal",
                "lengte": "1",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, "http://object.nl/api/v1/", "objects")
        mock_service_oas_get(m, "http://objecttypes.nl/api/v2/", "objecttypes")
        mock_resource_get(m, zaaktype)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([zaaktype]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={zaaktype['url']}",
            json=paginated_response([eigenschap]),
        )
        m.get(catalogus["url"], json=catalogus)

        core_config = CoreConfig.get_solo()
        objects_service = ServiceFactory.create(
            api_type=APITypes.orc, api_root="http://object.nl/api/v1/"
        )
        objecttypes_service = ServiceFactory.create(
            api_type=APITypes.orc, api_root="http://objecttypes.nl/api/v2/"
        )
        core_config.primary_objects_api = objects_service
        core_config.primary_objecttypes_api = objecttypes_service
        core_config.save()
        meta_config = MetaObjectTypesConfig.get_solo()
        meta_config.zaaktype_attribute_objecttype = "http://objecttype.nl/api/v2/objecttypes/5c3b34d1-e856-4c41-8d7e-fb03133f3a69"
        meta_config.save()
        m.get(
            "http://objecttypes.nl/api/v2/objecttypes",
            json=paginated_response(
                [
                    {
                        "url": "http://objecttypes.nl/api/v2/objecttypes/1",
                        "name": "zaaktypeAttribute",
                        "namePlural": "zaaktypeAttributes",
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
                    },
                ]
            ),
        )
        enum_obj = {
            "url": f"{objects_service.api_root}objects/0196252f-32de-4edb-90e8-10669b5dbf50",
            "uuid": "0196252f-32de-4edb-90e8-10669b5dbf50",
            "type": meta_config.zaaktype_attribute_objecttype,
            "record": {
                "index": 1,
                "typeVersion": 1,
                "data": {
                    "enum": ["3", "4"],
                    "naam": "some-property",
                    "waarde": "",
                    "zaaktypeCatalogus": catalogus["domein"],
                    "zaaktypeIdentificaties": [
                        zaaktype["identificatie"],
                    ],
                },
                "geometry": None,
                "startAt": "2022-08-08",
                "endAt": None,
                "registrationAt": "2022-08-08",
                "correctionFor": None,
                "correctedBy": None,
            },
        }

        m.post(
            f"{objects_service.api_root}objects/search",
            json=paginated_response([enum_obj]),
        )

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_identificatie": "ZT1"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(
            data,
            [
                {
                    "name": "some-property",
                    "spec": {
                        "type": "number",
                        "enum": [
                            {"label": "3", "value": 3.0},
                            {"label": "4", "value": 4.0},
                        ],
                    },
                }
            ],
        )
