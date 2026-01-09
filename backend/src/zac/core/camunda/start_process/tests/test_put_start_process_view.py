from unittest.mock import patch

from django.urls import reverse

import requests_mock
from django_camunda.utils import underscoreize
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import Eigenschap, RolType, ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.zaken import ZaakEigenschap
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import SuperUserFactory
from zac.api.context import ZaakContext
from zac.camunda.data import Task
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.rollen import Rol
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

from .utils import (
    CATALOGI_ROOT,
    DOCUMENTS_ROOT,
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    PROCESS_EIGENSCHAP,
    PROCESS_INFORMATIE_OBJECT,
    PROCESS_ROL,
    START_CAMUNDA_PROCESS_FORM,
    START_CAMUNDA_PROCESS_FORM_OBJ,
    START_CAMUNDA_PROCESS_FORM_OT,
    TASK_DATA,
    ZAKEN_ROOT,
)


def _get_task(**overrides):
    data = underscoreize({**TASK_DATA, **overrides})
    return factory(Task, data)


@requests_mock.Mocker()
class PutCamundaZaakProcessUserTaskViewTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = SuperUserFactory.create()

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        objecttypes_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTTYPES_ROOT
        )
        objects_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTS_ROOT
        )

        meta_config = MetaObjectTypesConfig.get_solo()
        meta_config.start_camunda_process_form_objecttype = (
            START_CAMUNDA_PROCESS_FORM_OT["url"]
        )
        meta_config.save()
        core_config = CoreConfig.get_solo()
        core_config.primary_objects_api = objects_service
        core_config.primary_objecttypes_api = objecttypes_service
        core_config.save()

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
            catalogus=catalogus_url,
            url=f"{CATALOGI_ROOT}zaaktypen/4f622c65-5ffe-476e-96ee-f0710bd0c92b",
            identificatie=START_CAMUNDA_PROCESS_FORM["zaaktypeIdentificaties"][0],
        )
        cls.eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            url=f"{CATALOGI_ROOT}eigenschappen/3941cb76-afc6-47d5-aa5d-6a9bfba963f6",
            zaaktype=cls.zaaktype["url"],
            naam=PROCESS_EIGENSCHAP["eigenschapnaam"],
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": ["aaa", "bbb"],
            },
            toelichting="some-toelichting",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            id="30a98ef3-bf35-4287-ac9c-fed048619dd7",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
        )
        cls.zaakeigenschap = generate_oas_component(
            "zrc",
            "schemas/ZaakEigenschap",
            url=f"{ZAKEN_ROOT}zaakeigenschappen/cc20d728-145b-4309-b797-9743826b220d",
            zaak=cls.zaak["url"],
            eigenschap=cls.eigenschap["url"],
            naam=cls.eigenschap["naam"],
            waarde="some-value-1",
        )
        cls.zaak["eigenschappen"] = [cls.zaakeigenschap]
        cls.informatieobjecttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            omschrijving=PROCESS_INFORMATIE_OBJECT["informatieobjecttypeOmschrijving"],
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.zaak["informatieobjecttypen"] = [cls.informatieobjecttype]
        cls.document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}informatieobject/e82ae0d6-d442-436e-be55-cf5b827dfeec",
            informatieobjecttype=cls.informatieobjecttype["url"],
        )
        cls.zaakinformatieobject = generate_oas_component(
            "zrc",
            "schemas/ZaakInformatieObject",
            informatieobject=cls.document["url"],
            zaak=cls.zaak["url"],
        )
        cls.roltype = generate_oas_component(
            "ztc",
            "schemas/RolType",
            url=f"{CATALOGI_ROOT}roltypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            zaaktype=cls.zaaktype["url"],
            omschrijvingGeneriek="klantcontacter",
            omschrijving=PROCESS_ROL["roltypeOmschrijving"],
        )
        cls.zaak["roltypen"] = [cls.roltype]
        cls.medewerker = generate_oas_component(
            "zrc",
            "schemas/RolMedewerker",
            identificatie="some-username",
            achternaam="Orange",
            voorletters="W.",
            voorvoegselAchternaam="van",
        )
        cls.rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            url=f"{ZAKEN_ROOT}rollen/5c2b8bf8-29a2-40bf-8c6c-7028aef896d4",
            zaak=cls.zaak["url"],
            betrokkene="",
            betrokkeneType=PROCESS_ROL["betrokkeneType"],
            roltype=cls.roltype["url"],
            betrokkene_identificatie=cls.medewerker,
            omschrijving=PROCESS_ROL["roltypeOmschrijving"],
            roltoelichting=PROCESS_ROL["roltypeOmschrijving"],
            omschrijving_generiek=cls.roltype["omschrijvingGeneriek"],
        )

        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )

        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)
        cls.zaak_context = ZaakContext(
            zaak=zaak,
            zaaktype=zaak.zaaktype,
        )

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
    )
    def test_put_start_process_user_task_everything_done(self, m, gt):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OT]),
        )
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}informatieobjecttypen",
            json=paginated_response([self.informatieobjecttype]),
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([self.rol]),
        )
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.roltype]),
        )
        mock_resource_get(m, self.roltype)
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.eigenschap]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaken/{self.zaak['id']}/zaakeigenschappen",
            json=[self.zaakeigenschap],
        )
        m.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={self.zaak['url']}",
            json=[self.zaakinformatieobject],
        )
        m.post(
            "https://camunda.example.com/engine-rest/task/598347ee-62fc-46a2-913a-6e0788bc1b8c/assignee",
            status_code=204,
        )
        m.post(
            "https://camunda.example.com/engine-rest/task/598347ee-62fc-46a2-913a-6e0788bc1b8c/complete",
            status_code=204,
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )
        ze = factory(ZaakEigenschap, self.zaakeigenschap)
        ze.eigenschap = factory(Eigenschap, self.eigenschap)
        with patch(
            "zac.core.services.get_rollen",
            return_value=[factory(Rol, self.rol)],
        ), patch(
            "zac.core.services.get_roltypen",
            return_value=[factory(RolType, self.roltype)],
        ), patch(
            "zac.core.services.get_zaakeigenschappen",
            return_value=[ze],
        ), patch(
            "zac.elasticsearch.searches.count_by_iot_in_zaak",
            return_value={self.informatieobjecttype["omschrijving"]: 1},
        ), patch(
            "zac.core.camunda.start_process.serializers.get_zaak_context",
            return_value=self.zaak_context,
        ):
            response = self.client.put(self.task_endpoint)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            m.last_request.json(),
            {
                "variables": {
                    "bptlAppId": {"type": "String", "value": ""},
                    "eigenschappen": {
                        "type": "Json",
                        "value": '[{"naam": "Some Eigenschap 1", "waarde": "some-value-1"}]',
                    },
                    "Some Eigenschap 1": {"type": "String", "value": "some-value-1"},
                    "Some Rol": {
                        "type": "Json",
                        "value": '{"betrokkeneType": "medewerker", "betrokkeneIdentificatie": {"identificatie": "some-username", "achternaam": "Orange", "voorletters": "W.", "voorvoegsel_achternaam": "van"}, "name": "W. van Orange", "omschrijving": "Some Rol", "roltoelichting": "Some Rol", "identificatie": "some-username"}',
                    },
                }
            },
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
    )
    @patch(
        "zac.core.services.get_rollen",
        return_value=[],
    )
    @patch(
        "zac.core.services.get_zaakeigenschappen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_rollen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_zaakeigenschappen",
        return_value=[],
    )
    def test_put_start_process_user_task_missing_bijlage(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OT]),
        )
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}informatieobjecttypen",
            json=paginated_response([self.informatieobjecttype]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={self.zaak['url']}",
            json=[self.zaakinformatieobject],
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )

        zaakcontext = ZaakContext(
            zaak=self.zaak_context.zaak,
            zaaktype=self.zaak_context.zaaktype,
        )
        with patch(
            "zac.elasticsearch.searches.count_by_iot_in_zaak",
            return_value=dict(),
        ):
            with patch(
                "zac.core.camunda.start_process.serializers.get_zaak_context",
                return_value=zaakcontext,
            ):
                response = self.client.put(self.task_endpoint)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "Een INFORMATIEOBJECT met INFORMATIEOBJECTTYPE `omschrijving`: `SomeDocument` is vereist.",
                }
            ],
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
    )
    @patch(
        "zac.elasticsearch.searches.count_by_iot_in_zaak",
        return_value=dict(),
    )
    @patch(
        "zac.core.services.get_zaakeigenschappen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_bijlagen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_zaakeigenschappen",
        return_value=[],
    )
    def test_put_start_process_user_task_missing_rol(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OT]),
        )
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.roltype]),
        )
        mock_resource_get(m, self.roltype)
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )

        with patch(
            "zac.core.camunda.start_process.serializers.get_zaak_context",
            return_value=self.zaak_context,
        ):
            response = self.client.put(self.task_endpoint)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "Vereiste ROLTYPE `omschrijving`: `Some Rol` is niet gevonden in ROLlen toebehorend aan ZAAK.",
                }
            ],
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
    )
    @patch(
        "zac.elasticsearch.searches.count_by_iot_in_zaak",
        return_value=dict(),
    )
    @patch(
        "zac.core.services.get_zaakeigenschappen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_bijlagen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_zaakeigenschappen",
        return_value=[],
    )
    def test_put_start_process_user_task_mismatch_rol_betrokkene_type(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OT]),
        )
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response(
                [{**self.rol, "betrokkeneType": "some-other-type"}]
            ),
        )
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.roltype]),
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )

        mock_resource_get(m, self.roltype)
        with patch(
            "zac.core.camunda.start_process.serializers.get_zaak_context",
            return_value=self.zaak_context,
        ):
            response = self.client.put(self.task_endpoint)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "`betrokkene_type` van ROL met ROLTYPE `omschrijving`: `Some Rol` komt niet overeen met vereist `betrokkene_type`: `medewerker`.",
                }
            ],
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
    )
    @patch(
        "zac.elasticsearch.searches.count_by_iot_in_zaak",
        return_value=dict(),
    )
    @patch(
        "zac.core.services.get_rollen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_bijlagen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_rollen",
        return_value=[],
    )
    def test_put_start_process_user_task_missing_eigenschap(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OT]),
        )
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.eigenschap]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaken/{self.zaak['id']}/zaakeigenschappen",
            json=[],
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )

        with patch(
            "zac.core.camunda.start_process.serializers.get_zaak_context",
            return_value=self.zaak_context,
        ):
            response = self.client.put(self.task_endpoint)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "Een ZAAKEIGENSCHAP met `naam`: `Some Eigenschap 1` is vereist.",
                }
            ],
        )
