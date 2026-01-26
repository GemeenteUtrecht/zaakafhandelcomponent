from unittest import mock
from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ResultaatType, ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.zaken import Resultaat
from zgw_consumers.constants import APITypes

from zac.accounts.tests.factories import (
    AccessRequestFactory,
    AtomicPermissionFactory,
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.core.camunda.start_process.tests.utils import (
    OBJECTS_ROOT,
    START_CAMUNDA_PROCESS_FORM,
)
from zac.core.permissions import (
    zaken_geforceerd_bijwerken,
    zaken_inzien,
    zaken_wijzigen,
)
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"


@requests_mock.Mocker()
class ZaakDetailResponseTests(ESMixin, ClearCachesMixin, APITestCase):
    """
    Test the API response body for zaak-detail endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        catalogus_url = (
            f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=catalogus_url,
            domein=START_CAMUNDA_PROCESS_FORM["zaaktypeCatalogus"],
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            startdatum="2020-12-25",
            uiterlijkeEinddatumAfdoening="2021-01-04",
            zaakgeometrie={"type": "Point", "coordinates": [4.4683077, 51.9236739]},
        )

        resultaattype = generate_oas_component(
            "ztc",
            "schemas/ResultaatType",
            url=f"{CATALOGI_ROOT}resultaattypen/362b23eb-d8a9-486f-b236-8adb58ebc18f",
            zaaktype=cls.zaaktype["url"],
            omschrijving="geannuleerd",
        )
        cls.resultaat = generate_oas_component(
            "zrc",
            "schemas/Resultaat",
            url=f"{ZAKEN_ROOT}resultaten/c8ebd02f-3265-4f2c-a7d7-f773ad7f589d",
            zaak=cls.zaak["url"],
            resultaattype=resultaattype["url"],
        )

        resultaat = factory(Resultaat, cls.resultaat)
        resultaat.resultaattype = factory(ResultaatType, resultaattype)
        cls.resultaat = {
            "url": cls.resultaat["url"],
            "resultaattype": {
                "url": resultaattype["url"],
                "omschrijving": resultaattype["omschrijving"],
            },
            "toelichting": cls.resultaat["toelichting"],
        }

        cls.patch_get_resultaat = patch(
            "zac.core.api.views.get_resultaat", return_value=resultaat
        )

        cls.detail_url = reverse(
            "zaak-detail",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )

        cls.patch_get_process_instances = patch(
            "zac.core.api.views.get_process_instances", return_value=dict()
        )
        cls.patch_views_fetch_start_camunda_process_form_for_zaaktype = patch(
            "zac.core.api.views.fetch_start_camunda_process_form_for_zaaktype",
            return_value=None,
        )
        cls.patch_serializers_fetch_start_camunda_process_form_for_zaaktype = patch(
            "zac.core.api.serializers.fetch_start_camunda_process_form_for_zaaktype",
            return_value=None,
        )
        cls.patch_serializers_get_camunda_variable_instances = patch(
            "zac.core.api.serializers.get_camunda_variable_instances", return_value=[]
        )

    def setUp(self):
        super().setUp()

        self.patch_get_resultaat.start()
        self.addCleanup(self.patch_get_resultaat.stop)
        self.patch_get_process_instances.start()
        self.addCleanup(self.patch_get_process_instances.stop)
        self.patch_views_fetch_start_camunda_process_form_for_zaaktype.start()
        self.addCleanup(
            self.patch_views_fetch_start_camunda_process_form_for_zaaktype.stop
        )
        self.patch_serializers_fetch_start_camunda_process_form_for_zaaktype.start()
        self.addCleanup(
            self.patch_serializers_fetch_start_camunda_process_form_for_zaaktype.stop
        )
        self.patch_serializers_get_camunda_variable_instances.start()
        self.addCleanup(self.patch_serializers_get_camunda_variable_instances.stop)

        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    @freeze_time("2020-12-26T12:00:00Z")
    def test_get_zaak_detail_indexed_in_es(self, m, *mocks):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)

        zaak_document = self.create_zaak_document(self.zaak)
        zaak_document.zaaktype = self.create_zaaktype_document(self.zaaktype)
        zaak_document.save()
        self.refresh_index()

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_response = {
            "url": f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            "identificatie": "ZAAK-2020-0010",
            "bronorganisatie": "123456782",
            "zaaktype": {
                "url": f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
                "catalogus": f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
                "omschrijving": self.zaaktype["omschrijving"],
                "versiedatum": self.zaaktype["versiedatum"],
            },
            "omschrijving": self.zaak["omschrijving"],
            "toelichting": self.zaak["toelichting"],
            "registratiedatum": self.zaak["registratiedatum"],
            "startdatum": "2020-12-25",
            "einddatum": None,
            "einddatumGepland": None,
            "vertrouwelijkheidaanduiding": "openbaar",
            "zaakgeometrie": {"type": "Point", "coordinates": [4.4683077, 51.9236739]},
            "deadline": "2021-01-04",
            "deadlineProgress": 10.00,
            "resultaat": self.resultaat,
            "kanGeforceerdBijwerken": True,
            "hasProcess": False,
            "isStatic": True,
            "isConfigured": False,
        }
        self.assertEqual(response.json(), expected_response)

    @freeze_time("2020-12-26T12:00:00Z")
    def test_not_indexed_in_es(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([self.zaak]),
        )

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_response = {
            "url": f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            "identificatie": "ZAAK-2020-0010",
            "bronorganisatie": "123456782",
            "zaaktype": {
                "url": f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
                "catalogus": f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
                "omschrijving": self.zaaktype["omschrijving"],
                "versiedatum": self.zaaktype["versiedatum"],
            },
            "omschrijving": self.zaak["omschrijving"],
            "toelichting": self.zaak["toelichting"],
            "registratiedatum": self.zaak["registratiedatum"],
            "startdatum": "2020-12-25",
            "einddatum": None,
            "einddatumGepland": None,
            "vertrouwelijkheidaanduiding": "openbaar",
            "zaakgeometrie": {"type": "Point", "coordinates": [4.4683077, 51.9236739]},
            "deadline": "2021-01-04",
            "deadlineProgress": 10.00,
            "resultaat": self.resultaat,
            "kanGeforceerdBijwerken": True,
            "hasProcess": False,
            "isStatic": True,
            "isConfigured": False,
        }
        self.assertEqual(response.json(), expected_response)

    def test_not_found(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([]),
        )

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @freeze_time("2020-12-26T12:00:00Z")
    def test_update_zaak_detail(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([self.zaak]),
        )

        m.patch(self.zaak["url"], status_code=status.HTTP_200_OK)

        response = self.client.patch(
            self.detail_url,
            {
                "einddatum": "2021-01-01",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.zeer_geheim,
                "zaakgeometrie": {
                    "type": "Point",
                    "coordinates": [4.4683077, 51.9236739],
                },
                "reden": "because",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(m.last_request.url, self.zaak["url"])
        self.assertEqual(
            m.last_request.json(),
            {
                "einddatum": "2021-01-01",
                "einddatum_gepland": None,
                "vertrouwelijkheidaanduiding": "zeer_geheim",  # String value, not enum
                "zaakgeometrie": {
                    "type": "Point",
                    "coordinates": [4.4683077, 51.9236739],
                },
            },
        )
        self.assertEqual(m.last_request.headers["X-Audit-Toelichting"], "because")

    @freeze_time("2020-12-26T12:00:00Z")
    def test_update_zaak_set_zaakgeometrie_null(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([self.zaak]),
        )

        m.patch(self.zaak["url"], status_code=status.HTTP_200_OK)

        response = self.client.patch(self.detail_url, {"zaakgeometrie": None})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(m.last_request.url, self.zaak["url"])
        self.assertEqual(m.last_request.json(), {"zaakgeometrie": None})

    def test_update_zaak_invalid_cache(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")

        m.post(f"{OBJECTS_ROOT}objects/search", json=paginated_response([]))
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([self.zaak]),
        )

        m.patch(self.zaak["url"], status_code=status.HTTP_200_OK)

        # populate cache
        get_response = self.client.get(self.detail_url)

        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        cache_find_key = (
            f"zaak:{self.zaak['bronorganisatie']}:{self.zaak['identificatie']}"
        )
        self.assertIsNotNone(cache.get(cache_find_key))

        # patch
        response = self.client.patch(
            self.detail_url,
            {
                "einddatum": "2021-01-01",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.zeer_geheim,
                "reden": "because",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        #  cache is cleaned
        self.assertIsNone(cache.get(cache_find_key))

    @freeze_time("2020-12-26T12:00:00Z")
    def test_change_va_without_reden_invalid(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([self.zaak]),
        )
        m.patch(self.zaak["url"], status_code=status.HTTP_200_OK)

        response = self.client.patch(
            self.detail_url,
            {
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "'reden' is required when 'vertrouwelijkheidaanduiding' is changed",
                }
            ],
        )

    @freeze_time("2020-12-26T12:00:00Z")
    def test_change_va_without_reden_valid(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([self.zaak]),
        )
        m.patch(self.zaak["url"], status_code=status.HTTP_200_OK)

        response = self.client.patch(
            self.detail_url,
            {
                "vertrouwelijkheidaanduiding": self.zaak["vertrouwelijkheidaanduiding"],
                "omschrijving": "new desc",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(m.last_request.url, self.zaak["url"])
        self.assertEqual(
            m.last_request.json(),
            {
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.openbaar,
                "omschrijving": "new desc",
            },
        )
        self.assertFalse("X-Audit-Toelichting" in m.last_request.headers)

    def test_change_without_reden_valid(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([self.zaak]),
        )
        m.patch(self.zaak["url"], status_code=status.HTTP_200_OK)

        response = self.client.patch(
            self.detail_url,
            {
                "omschrijving": "new desc",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(m.last_request.url, self.zaak["url"])
        self.assertEqual(
            m.last_request.json(),
            {
                "omschrijving": "new desc",
            },
        )
        self.assertFalse("X-Audit-Toelichting" in m.last_request.headers)

    def test_update_with_blank_toelichting(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([self.zaak]),
        )
        m.patch(self.zaak["url"], status_code=status.HTTP_200_OK)

        data = {
            "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.openbaar,
            "reden": "some",
            "omschrijving": "new desc",
            "toelichting": "",
        }

        response = self.client.patch(self.detail_url, data)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(m.last_request.url, self.zaak["url"])
        self.assertEqual(
            m.last_request.json(),
            {
                "omschrijving": "new desc",
                "toelichting": "",
                "vertrouwelijkheidaanduiding": "openbaar",
            },
        )
        self.assertEqual(m.last_request.headers["X-Audit-Toelichting"], "some")

    @override_settings(CREATE_ZAAK_PROCESS_DEFINITION_KEY="some-start-key")
    @freeze_time("2020-12-26T12:00:00Z")
    def test_has_process(self, m, *othermocks):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([self.zaak]),
        )

        with self.subTest("No process instances -> hasProcess = False"):
            response = self.client.get(self.detail_url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertFalse(response.json()["hasProcess"])

        with self.subTest(
            "Process instance with def key other than settings.CREATE_ZAAK_PROCESS... -> hasProcess = True"
        ):
            process_instance = mock.MagicMock()
            process_definition = mock.MagicMock()
            type(process_definition).key = mock.PropertyMock(
                return_value="some-model-key"
            )
            process_instance.process_definition = process_definition

            with patch(
                "zac.core.api.views.get_process_instances",
                return_value={str(process_instance.id): process_instance},
            ):
                response = self.client.get(self.detail_url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.json()["hasProcess"])

        with self.subTest(
            "Same definition key as settings.CREATE_ZAAK_PROCESS... has incidents."
        ):
            process_instance = mock.MagicMock()
            process_definition = mock.MagicMock()
            type(process_definition).key = mock.PropertyMock(
                return_value="some-start-key"
            )
            process_instance.definition = process_definition

            with patch(
                "zac.core.api.views.get_process_instances",
                return_value={str(process_instance.id): process_instance},
            ):
                with patch(
                    "zac.core.api.serializers.get_incidents_for_process_instance",
                    return_value=["some incident"],
                ):
                    with patch(
                        "zac.core.api.serializers.get_camunda_variable_instances",
                        return_value=[],
                    ):
                        with patch("zac.core.api.serializers.logger") as logger:
                            response = self.client.get(self.detail_url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertFalse(response.json()["hasProcess"])
            logger.error.assert_called_once_with(
                "Something went wrong. An incident was reported in Camunda."
            )

        with self.subTest(
            "Process instance with def key same as settings.CREATE_ZAAK... has no incidents but also no startRelatedBusinessProcess var"
        ):
            with patch(
                "zac.core.api.views.get_process_instances",
                return_value={str(process_instance.id): process_instance},
            ):
                with patch(
                    "zac.core.api.serializers.get_incidents_for_process_instance",
                    return_value=[],
                ):
                    with patch(
                        "zac.core.api.serializers.get_camunda_variable_instances",
                        return_value=[],
                    ):
                        response = self.client.get(self.detail_url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertFalse(response.json()["hasProcess"])

        ## Process instance with definition key same as CREATE_ZAAK_PROCESS_DEFINITION_KEY
        #  has no incidents and a variable named startRelatedBusinessProcess but no camunda start process form.

        with self.subTest(
            "Process instance with def key same as settings.CREATE_ZAAK... has no incidents, has startRelatedBusinessProcess var but no form"
        ):
            with patch(
                "zac.core.api.views.get_process_instances",
                return_value={str(process_instance.id): process_instance},
            ):
                with patch(
                    "zac.core.api.serializers.get_incidents_for_process_instance",
                    return_value=[],
                ):
                    with patch(
                        "zac.core.api.serializers.get_camunda_variable_instances",
                        return_value=[{"variableName": "startRelatedBusinessProcess"}],
                    ):
                        response = self.client.get(self.detail_url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertFalse(response.json()["hasProcess"])

        ## Process instance with definition key same as CREATE_ZAAK_PROCESS_DEFINITION_KEY
        #  has no incidents and a variable named startRelatedBusinessProcess and a camunda start process form.
        with self.subTest(
            "Process instance with def key same as settings.CREATE_ZAAK.... has no incidents, has startRelatedBusinessProcess and a form"
        ):
            with patch(
                "zac.core.api.views.get_process_instances",
                return_value={str(process_instance.id): process_instance},
            ):
                with patch(
                    "zac.core.api.serializers.get_incidents_for_process_instance",
                    return_value=[],
                ):
                    with patch(
                        "zac.core.api.serializers.get_camunda_variable_instances",
                        return_value=[{"variableName": "startRelatedBusinessProcess"}],
                    ):
                        with patch(
                            "zac.core.api.views.fetch_start_camunda_process_form_for_zaaktype",
                            return_value="some-form",
                        ):
                            response = self.client.get(self.detail_url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.json()["hasProcess"])

    @freeze_time("2020-12-26T12:00:00Z")
    def test_is_static(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        mock_resource_get(m, self.catalogus)
        mock_resource_get(
            m, {**self.zaaktype, "identificatie": "some-other-identificatie"}
        )
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([self.zaak]),
        )

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_response = {
            "url": f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            "identificatie": "ZAAK-2020-0010",
            "bronorganisatie": "123456782",
            "zaaktype": {
                "url": f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
                "catalogus": f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
                "omschrijving": self.zaaktype["omschrijving"],
                "versiedatum": self.zaaktype["versiedatum"],
            },
            "omschrijving": self.zaak["omschrijving"],
            "toelichting": self.zaak["toelichting"],
            "registratiedatum": self.zaak["registratiedatum"],
            "startdatum": "2020-12-25",
            "einddatum": None,
            "einddatumGepland": None,
            "vertrouwelijkheidaanduiding": "openbaar",
            "zaakgeometrie": {"type": "Point", "coordinates": [4.4683077, 51.9236739]},
            "deadline": "2021-01-04",
            "deadlineProgress": 10.00,
            "resultaat": self.resultaat,
            "kanGeforceerdBijwerken": True,
            "hasProcess": False,
            "isStatic": True,
            "isConfigured": False,
        }
        self.assertEqual(response.json(), expected_response)

    @freeze_time("2020-12-26T12:00:00Z")
    def test_is_configured(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([self.zaak]),
        )
        process_instance = mock.MagicMock()

        with patch(
            "zac.core.api.views.get_process_instances",
            return_value={str(process_instance.id): process_instance},
        ):
            with patch(
                "zac.core.api.serializers.get_camunda_variable_instances",
                return_value=[{"variableName": "startRelatedBusinessProcess"}],
            ):
                response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_response = {
            "url": f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            "identificatie": "ZAAK-2020-0010",
            "bronorganisatie": "123456782",
            "zaaktype": {
                "url": f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
                "catalogus": f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
                "omschrijving": self.zaaktype["omschrijving"],
                "versiedatum": self.zaaktype["versiedatum"],
            },
            "omschrijving": self.zaak["omschrijving"],
            "toelichting": self.zaak["toelichting"],
            "registratiedatum": self.zaak["registratiedatum"],
            "startdatum": "2020-12-25",
            "einddatum": None,
            "einddatumGepland": None,
            "vertrouwelijkheidaanduiding": "openbaar",
            "zaakgeometrie": {"type": "Point", "coordinates": [4.4683077, 51.9236739]},
            "deadline": "2021-01-04",
            "deadlineProgress": 10.00,
            "resultaat": self.resultaat,
            "kanGeforceerdBijwerken": True,
            "hasProcess": True,
            "isStatic": True,
            "isConfigured": True,
        }
        self.assertEqual(response.json(), expected_response)

    @freeze_time("2020-12-26T12:00:00Z")
    def test_is_configured_empty_list_of_process_instances_regression(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([self.zaak]),
        )
        process_instance = mock.MagicMock()

        with patch(
            "zac.core.api.views.get_process_instances",
            return_value=dict(),
        ):
            with patch(
                "zac.core.api.serializers.get_camunda_variable_instances",
                return_value=[{"variableName": "startRelatedBusinessProcess"}],
            ):
                response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_response = {
            "url": f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            "identificatie": "ZAAK-2020-0010",
            "bronorganisatie": "123456782",
            "zaaktype": {
                "url": f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
                "catalogus": f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
                "omschrijving": self.zaaktype["omschrijving"],
                "versiedatum": self.zaaktype["versiedatum"],
            },
            "omschrijving": self.zaak["omschrijving"],
            "toelichting": self.zaak["toelichting"],
            "registratiedatum": self.zaak["registratiedatum"],
            "startdatum": "2020-12-25",
            "einddatum": None,
            "einddatumGepland": None,
            "vertrouwelijkheidaanduiding": "openbaar",
            "zaakgeometrie": {"type": "Point", "coordinates": [4.4683077, 51.9236739]},
            "deadline": "2021-01-04",
            "deadlineProgress": 10.00,
            "resultaat": self.resultaat,
            "kanGeforceerdBijwerken": True,
            "hasProcess": False,
            "isStatic": True,
            "isConfigured": False,
        }
        self.assertEqual(response.json(), expected_response)


class ZaakDetailPermissionTests(ESMixin, ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOME",
        )
        cls._zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        cls.zaaktype = factory(ZaakType, cls._zaaktype)
        cls._zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype.url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        cls.zaak = factory(Zaak, cls._zaak)
        cls.zaak.zaaktype = cls.zaaktype
        cls.find_zaak_patcher = patch(
            "zac.core.api.views.find_zaak", return_value=cls.zaak
        )
        cls.patch_get_process_instances = patch(
            "zac.core.api.views.get_process_instances",
            return_value=dict(),
        )
        cls.patch_get_camunda_variable_instances = patch(
            "zac.core.api.serializers.get_camunda_variable_instances", return_value=[]
        )
        cls.detail_url = reverse(
            "zaak-detail",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )

    def setUp(self):
        super().setUp()

        self.find_zaak_patcher.start()
        self.addCleanup(self.find_zaak_patcher.stop)

        self.patch_get_process_instances.start()
        self.addCleanup(self.patch_get_process_instances.stop)

        self.patch_get_camunda_variable_instances.start()
        self.addCleanup(self.patch_get_camunda_variable_instances.stop)

    def test_not_authenticated(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.patch(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_authenticated_no_permissions(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self._zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={self.zaak.bronorganisatie}&identificatie={self.zaak.identificatie}",
            json=paginated_response([self._zaak]),
        )

        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.patch(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.json(),
            {
                "canRequestAccess": True,
                "reason": "De gebruiker heeft niet de vereiste rechten.",
            },
        )

    @requests_mock.Mocker()
    def test_has_perm_but_not_for_zaaktype(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self._zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={self.zaak.bronorganisatie}&identificatie={self.zaak.identificatie}",
            json=paginated_response([self._zaak]),
        )
        # gives them access to the page, but no catalogus specified -> nothing visible
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": "",
                "zaaktype_omschrijving": "",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.json(),
            {
                "canRequestAccess": True,
                "reason": "De gebruiker heeft niet de vereiste rechten.",
            },
        )

    @requests_mock.Mocker()
    def test_has_perm_but_not_for_va(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self._zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={self.zaak.bronorganisatie}&identificatie={self.zaak.identificatie}",
            json=paginated_response([self._zaak]),
        )
        user = UserFactory.create()
        # gives them access to the page and zaaktype, but insufficient VA
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.json(),
            {
                "canRequestAccess": True,
                "reason": "De gebruiker heeft niet de vereiste rechten.",
            },
        )

    @requests_mock.Mocker()
    def test_has_already_requested(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self._zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={self.zaak.bronorganisatie}&identificatie={self.zaak.identificatie}",
            json=paginated_response([self._zaak]),
        )
        user = UserFactory.create()
        AccessRequestFactory.create(requester=user, zaak=self.zaak.url)
        self.client.force_authenticate(user=user)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.json(),
            {
                "canRequestAccess": False,
                "reason": "Je hebt al een toegangsverzoek voor deze ZAAK",
            },
        )

    @requests_mock.Mocker()
    def test_has_perm_to_retrieve(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype.catalogus}",
            json=paginated_response([self._zaaktype]),
        )
        user = UserFactory.create()
        # gives them access to the page, zaaktype and VA specified -> visible
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @requests_mock.Mocker()
    def test_has_perm_to_update(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype.catalogus}",
            json=paginated_response([self._zaaktype]),
        )
        user = UserFactory.create()

        # allows them to update details on the case
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

        m.patch(self.zaak.url, status_code=status.HTTP_200_OK)
        response = self.client.patch(
            self.detail_url,
            {
                "einddatum": "2021-01-01",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.zeer_geheim,
                "reden": "because",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @requests_mock.Mocker()
    def test_has_perm_to_update_but_zaak_is_closed(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self._zaaktype)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype.catalogus}",
            json=paginated_response([self._zaaktype]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={self.zaak.bronorganisatie}&identificatie={self.zaak.identificatie}",
            json=paginated_response([self._zaak]),
        )
        user = UserFactory.create()

        # allows them to update details on the case
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

        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=self.zaaktype.url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            einddatum="2020-01-01",
        )
        zaak = factory(Zaak, zaak)
        m.patch(zaak.url, status_code=status.HTTP_200_OK)
        with patch("zac.core.api.views.find_zaak", return_value=zaak):
            response = self.client.patch(
                self.detail_url,
                {
                    "einddatum": "2021-01-01",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.zeer_geheim,
                    "reden": "because",
                },
            )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_to_update_and_for_closed_zaak(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self._zaaktype)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype.catalogus}",
            json=paginated_response([self._zaaktype]),
        )
        user = UserFactory.create()

        # allows them to update details on the case
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

        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=self.zaaktype.url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            einddatum="2020-01-01",
        )
        zaak = factory(Zaak, zaak)
        m.patch(zaak.url, status_code=status.HTTP_200_OK)
        with patch("zac.core.api.views.find_zaak", return_value=zaak):
            response = self.client.patch(
                self.detail_url,
                {
                    "einddatum": "2021-01-01",
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.zeer_geheim,
                    "reden": "because",
                },
            )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_has_atomic_access(self):
        user = UserFactory.create()
        AtomicPermissionFactory.create(
            object_url=self.zaak.url,
            permission=zaken_inzien.name,
            for_user=user,
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
