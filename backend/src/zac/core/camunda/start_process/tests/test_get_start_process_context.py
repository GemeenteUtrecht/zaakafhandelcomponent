from unittest.mock import patch

from django.urls import reverse

import requests_mock
from django_camunda.utils import underscoreize
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import InformatieObjectType, ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import SuperUserFactory
from zac.api.context import ZaakContext
from zac.camunda.data import Task
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.tests.utils import ClearCachesMixin
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
class GetCamundaZaakProcessContextUserTaskViewTests(ClearCachesMixin, APITestCase):
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
            zaaktype=cls.zaaktype["url"],
            naam=PROCESS_EIGENSCHAP["eigenschapnaam"],
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": ["aaa", "bbb"],
            },
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
            url=f"{ZAKEN_ROOT}/zaakeigenschappen/cc20d728-145b-4309-b797-9743826b220d",
            zaak=cls.zaak["url"],
            eigenschap=cls.eigenschap["url"],
            naam=cls.eigenschap["naam"],
            waarde="aaa",
        )
        cls.informatieobjecttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            omschrijving=PROCESS_INFORMATIE_OBJECT["informatieobjecttypeOmschrijving"],
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            informatieobjecttype=cls.informatieobjecttype["url"],
        )

        cls.medewerker = generate_oas_component(
            "zrc",
            "schemas/RolMedewerker",
            identificatie="some-username",
            achternaam="Orange",
            voorletters="W.",
            voorvoegselAchternaam="van",
        )
        cls.roltype = generate_oas_component(
            "ztc",
            "schemas/RolType",
            url=f"{CATALOGI_ROOT}roltypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            zaaktype=cls.zaaktype["url"],
            omschrijvingGeneriek="klantcontacter",
            omschrijving=PROCESS_ROL["roltypeOmschrijving"],
        )
        cls.rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=cls.zaak["url"],
            betrokkene="",
            betrokkeneType=PROCESS_ROL["betrokkeneType"],
            roltype=cls.roltype["url"],
            betrokkeneIdentificatie=cls.medewerker,
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
    def test_get_start_process_context_user_task_everything_done(self, m, gt):
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
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.eigenschap]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaken/{self.zaak['id']}/zaakeigenschappen",
            json=[self.zaakeigenschap],
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )

        with patch(
            "zac.core.camunda.start_process.utils.count_by_iot_in_zaak",
            return_value={self.informatieobjecttype["omschrijving"]: 1},
        ):
            with patch(
                "zac.core.camunda.start_process.serializers.get_zaak_context",
                return_value=self.zaak_context,
            ):
                with patch(
                    "zac.core.camunda.start_process.utils.get_informatieobjecttypen_for_zaaktype",
                    return_value=[
                        factory(InformatieObjectType, self.informatieobjecttype)
                    ],
                ):
                    response = self.client.get(self.task_endpoint)
        self.assertEqual(
            response.json(),
            {
                "form": "zac:startProcessForm",
                "task": {
                    "id": "598347ee-62fc-46a2-913a-6e0788bc1b8c",
                    "name": "aName",
                    "created": "2013-01-23T11:42:42Z",
                    "hasForm": False,
                    "assigneeType": "",
                    "canCancelTask": False,
                    "assignee": None,
                    "formKey": "zac:startProcessForm",
                },
                "context": {
                    "benodigdeBijlagen": [
                        {
                            "informatieobjecttype": {
                                "url": self.informatieobjecttype["url"],
                                "omschrijving": self.informatieobjecttype[
                                    "omschrijving"
                                ],
                            },
                            "alreadyUploadedInformatieobjecten": 1,
                            "allowMultiple": True,
                            "label": PROCESS_INFORMATIE_OBJECT["label"],
                            "required": True,
                            "order": 1,
                        }
                    ],
                    "benodigdeRollen": [],
                    "benodigdeZaakeigenschappen": [],
                },
            },
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
    )
    def test_get_start_process_context_user_task_missing_everything(self, m, gt):
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
            json=paginated_response([]),
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
            f"{ZAKEN_ROOT}zaken/{self.zaak['id']}/zaakeigenschappen",
            json=[],
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )

        zaak_context = ZaakContext(
            zaak=self.zaak_context.zaak,
            zaaktype=self.zaak_context.zaaktype,
        )

        with patch(
            "zac.core.camunda.start_process.utils.count_by_iot_in_zaak",
            return_value=dict(),
        ):
            with patch(
                "zac.core.camunda.start_process.serializers.get_zaak_context",
                return_value=zaak_context,
            ):
                with patch(
                    "zac.core.camunda.start_process.utils.get_informatieobjecttypen_for_zaaktype",
                    return_value=[
                        factory(InformatieObjectType, self.informatieobjecttype)
                    ],
                ):
                    response = self.client.get(self.task_endpoint)
        self.assertEqual(
            response.json(),
            {
                "form": "zac:startProcessForm",
                "task": {
                    "id": "598347ee-62fc-46a2-913a-6e0788bc1b8c",
                    "name": "aName",
                    "created": "2013-01-23T11:42:42Z",
                    "hasForm": False,
                    "assigneeType": "",
                    "canCancelTask": False,
                    "assignee": None,
                    "formKey": "zac:startProcessForm",
                },
                "context": {
                    "benodigdeBijlagen": [
                        {
                            "informatieobjecttype": {
                                "url": "http://catalogus.nl/api/v1/informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
                                "omschrijving": PROCESS_INFORMATIE_OBJECT[
                                    "informatieobjecttypeOmschrijving"
                                ],
                            },
                            "alreadyUploadedInformatieobjecten": 0,
                            "allowMultiple": True,
                            "label": PROCESS_INFORMATIE_OBJECT["label"],
                            "required": True,
                            "order": 1,
                        }
                    ],
                    "benodigdeRollen": [
                        {
                            "roltype": {
                                "url": "http://catalogus.nl/api/v1/roltypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
                                "omschrijving": PROCESS_ROL["roltypeOmschrijving"],
                                "omschrijvingGeneriek": "klantcontacter",
                            },
                            "label": PROCESS_ROL["label"],
                            "betrokkeneType": PROCESS_ROL["betrokkeneType"],
                            "required": True,
                            "order": 1,
                        }
                    ],
                    "benodigdeZaakeigenschappen": [
                        {
                            "eigenschap": {
                                "url": self.eigenschap["url"],
                                "naam": self.eigenschap["naam"],
                                "toelichting": self.eigenschap["toelichting"],
                                "specificatie": {
                                    "groep": "dummy",
                                    "formaat": "tekst",
                                    "lengte": "3",
                                    "kardinaliteit": "1",
                                    "waardenverzameling": ["aaa", "bbb"],
                                },
                            },
                            "label": PROCESS_EIGENSCHAP["label"],
                            "default": "",
                            "required": True,
                            "order": 1,
                            "choices": [
                                {"label": "aaa", "value": "aaa"},
                                {"label": "bbb", "value": "bbb"},
                            ],
                        }
                    ],
                },
            },
        )
