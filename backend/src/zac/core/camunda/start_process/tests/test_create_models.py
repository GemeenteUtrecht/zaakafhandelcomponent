from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

import requests_mock
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import (
    Eigenschap,
    InformatieObjectType,
    RolType,
    ZaakType,
)
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.tests.utils import paginated_response

from ..models import (
    CamundaStartProcess,
    ProcessEigenschap,
    ProcessInformatieObject,
    ProcessRol,
)

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"


@requests_mock.Mocker()
class StartProcessModelsTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        catalogus_url = (
            f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus_url,
            url=f"{CATALOGI_ROOT}zaaktypen/4f622c65-5ffe-476e-96ee-f0710bd0c92b",
        )
        cls.roltype = generate_oas_component(
            "ztc",
            "schemas/RolType",
            url=f"{CATALOGI_ROOT}roltypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            zaaktype=cls.zaaktype["url"],
            omschrijvingGeneriek="klantcontacter",
            omschrijving="some-omschrijving",
        )
        cls.eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=cls.zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": ["aaa", "bbb"],
            },
        )
        cls.informatieobjecttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            omschrijving="bijlage",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.ziot = generate_oas_component(
            "ztc",
            "schemas/ZaakTypeInformatieObjectType",
            zaaktype=cls.zaaktype["url"],
            informatieobjecttype=cls.informatieobjecttype["url"],
            volgnummer=1,
        )
        cls.patcher_get_informatieobjecttype = patch(
            "zac.core.services.get_informatieobjecttype",
            return_value=factory(InformatieObjectType, cls.informatieobjecttype),
        )

    def setUp(self):
        super().setUp()
        self.patcher_get_informatieobjecttype.start()
        self.addCleanup(self.patcher_get_informatieobjecttype.stop)

    def test_create_camunda_start_process(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.roltype]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.eigenschap]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.ziot]),
        )
        camunda_start_process = CamundaStartProcess.objects.create(
            zaaktype_catalogus=self.zaaktype["catalogus"],
            zaaktype_identificatie=self.zaaktype["identificatie"],
        )
        zaaktype = factory(ZaakType, self.zaaktype)
        self.assertEqual(camunda_start_process.zaaktype, zaaktype)
        roltypen = factory(RolType, [self.roltype])
        self.assertEqual(camunda_start_process.roltypen, roltypen)
        eigenschap = factory(Eigenschap, self.eigenschap)
        eigenschap.zaaktype = zaaktype
        eigenschappen = [eigenschap]

        self.assertEqual(camunda_start_process.eigenschappen, eigenschappen)
        self.assertEqual(
            camunda_start_process.informatieobjecttypen,
            factory(InformatieObjectType, [self.informatieobjecttype]),
        )

    def test_create_process_eigenschap_success(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.eigenschap]),
        )
        camunda_start_process = CamundaStartProcess.objects.create(
            zaaktype_catalogus=self.zaaktype["catalogus"],
            zaaktype_identificatie=self.zaaktype["identificatie"],
        )

        pei = ProcessEigenschap(
            camunda_start_process=camunda_start_process,
            label="some-label",
            eigenschapnaam=self.eigenschap["naam"],
        )
        pei.clean()

    def test_create_process_eigenschap_fail(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.eigenschap]),
        )
        camunda_start_process = CamundaStartProcess.objects.create(
            zaaktype_catalogus=self.zaaktype["catalogus"],
            zaaktype_identificatie=self.zaaktype["identificatie"],
        )
        pei = ProcessEigenschap(
            camunda_start_process=camunda_start_process,
            label="some-label",
            eigenschapnaam="some-faulty-name",
        )
        with self.assertRaises(ValidationError):
            pei.clean()

    def test_create_process_informatieobject_success(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.ziot]),
        )
        camunda_start_process = CamundaStartProcess.objects.create(
            zaaktype_catalogus=self.zaaktype["catalogus"],
            zaaktype_identificatie=self.zaaktype["identificatie"],
        )

        pio = ProcessInformatieObject(
            camunda_start_process=camunda_start_process,
            label="some-label",
            informatieobjecttype_omschrijving=self.informatieobjecttype["omschrijving"],
            allow_multiple=False,
            required=False,
        )
        pio.clean()

    def test_create_process_informatieobject_fail(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.ziot]),
        )
        camunda_start_process = CamundaStartProcess.objects.create(
            zaaktype_catalogus=self.zaaktype["catalogus"],
            zaaktype_identificatie=self.zaaktype["identificatie"],
        )

        pio = ProcessInformatieObject(
            camunda_start_process=camunda_start_process,
            label="some-label",
            informatieobjecttype_omschrijving="some-faulty-omschrijving",
            allow_multiple=False,
            required=False,
        )
        with self.assertRaises(ValidationError):
            pio.clean()

    def test_create_process_rol_success(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.roltype]),
        )
        camunda_start_process = CamundaStartProcess.objects.create(
            zaaktype_catalogus=self.zaaktype["catalogus"],
            zaaktype_identificatie=self.zaaktype["identificatie"],
        )

        pr = ProcessRol(
            camunda_start_process=camunda_start_process,
            label="some-label",
            roltype_omschrijving=self.roltype["omschrijving"],
            required=False,
        )
        pr.clean()

    def test_create_process_rol_fail(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.roltype]),
        )
        camunda_start_process = CamundaStartProcess.objects.create(
            zaaktype_catalogus=self.zaaktype["catalogus"],
            zaaktype_identificatie=self.zaaktype["identificatie"],
        )

        pr = ProcessRol(
            camunda_start_process=camunda_start_process,
            label="some-label",
            roltype_omschrijving="some-faulty-omschrijving",
            required=False,
        )
        with self.assertRaises(ValidationError):
            pr.clean()
