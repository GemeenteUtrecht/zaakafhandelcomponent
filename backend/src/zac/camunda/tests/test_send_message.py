import uuid
from unittest.mock import patch

from django.urls import reverse

import requests_mock
from django_camunda.client import get_client
from django_camunda.models import CamundaConfig
from django_camunda.utils import serialize_variable
from rest_framework import exceptions, status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import BlueprintPermissionFactory, UserFactory
from zac.core.models import CoreConfig
from zac.core.permissions import zaakproces_send_message
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

from ..api.serializers import MessageSerializer
from ..data import ProcessInstance

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CAMUNDA_ROOT = "https://some.camunda.nl/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"


def _get_camunda_client():
    config = CamundaConfig.get_solo()
    config.root_url = CAMUNDA_ROOT
    config.rest_api_path = CAMUNDA_API_PATH
    config.save()
    return get_client()


class SendMessageSerializerTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls._uuid = uuid.uuid4()
        cls.message = {
            "message": "some-message",
            "process_instance_id": cls._uuid,
        }

    def test_message_serializer_fail_validation(self):
        message_serializer = MessageSerializer(data=self.message)

        with self.assertRaises(exceptions.ValidationError) as exc:
            message_serializer.is_valid(raise_exception=True)
            self.assertEqual(exc.code, "invalid_choice")

    def test_message_serializer_set_message(self):
        message_serializer = MessageSerializer(data=self.message)
        message_serializer.set_message_choices(
            [self.message["message"], "some-other-message"]
        )
        message_serializer.is_valid(raise_exception=True)

        self.assertEqual(message_serializer.validated_data, self.message)


class SendMessagePermissionAndResponseTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            startdatum="2020-12-25",
            uiterlijkeEinddatumAfdoening="2021-01-04",
        )

        process_instance_id = uuid.uuid4()
        process_definition_id = uuid.uuid4()
        definition_id = f"BBV_vragen:3:{process_definition_id}"
        cls.process_instance = {
            "id": str(process_instance_id),
            "definition_id": definition_id,
        }

        process_instance = factory(ProcessInstance, cls.process_instance)

        cls.patch_get_process_instance = patch(
            "zac.camunda.api.views.get_process_instance",
            return_value=process_instance,
        )
        cls.patch_get_messages = patch(
            "zac.camunda.api.views.get_messages",
            return_value=["some-message", "some-other-message"],
        )

        cls.patch_get_process_zaak_url = patch(
            "zac.camunda.api.views.get_process_zaak_url",
            return_value=None,
        )

        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)

        cls.patch_get_zaak = patch(
            "zac.camunda.api.views.get_zaak",
            return_value=zaak,
        )

        cls.endpoint = reverse("send-message")

        cls.core_config = CoreConfig.get_solo()
        cls.core_config.app_id = "http://some-open-zaak-url.nl/with/uuid/"
        cls.core_config.save()

        cls.patch_get_camunda_client = patch(
            "zac.camunda.api.views.get_client", return_value=_get_camunda_client()
        )

    def setUp(self):
        super().setUp()

        self.patch_get_process_instance.start()
        self.addCleanup(self.patch_get_process_instance.stop)

        self.patch_get_messages.start()
        self.addCleanup(self.patch_get_messages.stop)

        self.patch_get_process_zaak_url.start()
        self.addCleanup(self.patch_get_process_zaak_url.stop)

        self.patch_get_zaak.start()
        self.addCleanup(self.patch_get_zaak.stop)

        self.patch_get_camunda_client.start()
        self.addCleanup(self.patch_get_camunda_client.stop)

    def test_not_authenticated(self):
        response = self.client.post(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.post(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        user = UserFactory.create()

        # gives them access to the page, zaaktype and VA specified -> visible
        # and allows them to send messages
        BlueprintPermissionFactory.create(
            role__permissions=[zaakproces_send_message.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )

        self.client.force_authenticate(user=user)

        m.post(
            f"{CAMUNDA_URL}message",
            status_code=201,
            json=[{"variables": {"waitForIt": serialize_variable(True)}}],
        )

        data = {
            "message": "some-message",
            "process_instance_id": self.process_instance["id"],
        }
        response = self.client.post(
            self.endpoint,
            data=data,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json(), {"waitForIt": True})

        expected_payload = {
            "messageName": data["message"],
            "processInstanceId": data["process_instance_id"],
            "processVariables": {
                "bptlAppId": serialize_variable(self.core_config.app_id)
            },
            "resultEnabled": True,
            "variablesInResultEnabled": True,
        }
        self.assertEqual(m.last_request.json(), expected_payload)
