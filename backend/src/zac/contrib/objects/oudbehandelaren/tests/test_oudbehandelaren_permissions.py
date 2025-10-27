from unittest.mock import patch

from django.urls import reverse_lazy

import requests_mock
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    AtomicPermissionFactory,
    BlueprintPermissionFactory,
    UserFactory,
)
from zac.contrib.objects.oudbehandelaren.data import Oudbehandelaren
from zac.core.api.permissions import zaken_inzien
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models import Zaak

from .factories import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    IDENTIFICATIE,
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    ZAAK_URL,
    ZAKEN_ROOT,
    OudbehandelarenObjectFactory,
    OudbehandelarenObjectTypeFactory,
)

OUDBEHANDELAREN_OBJECTTYPE = OudbehandelarenObjectTypeFactory()


@requests_mock.Mocker()
class OudbehandelarenApiPermissionsTests(ClearCachesMixin, APITestCase):
    endpoint = reverse_lazy(
        "zaak-oudbehandelaren",
        kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE},
    )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            domein="UTRE",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=cls.catalogus["url"],
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            zaaktype=cls.zaaktype["url"],
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            einddatum=None,
        )
        objects_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTS_ROOT
        )
        objecttypes_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTTYPES_ROOT
        )
        config = CoreConfig.get_solo()
        config.primary_objects_api = objects_service
        config.primary_objecttypes_api = objecttypes_service
        config.save()

        meta_config = MetaObjectTypesConfig.get_solo()
        meta_config.oudbehandelaren_objecttype = OUDBEHANDELAREN_OBJECTTYPE["url"]
        meta_config.save()

        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
        )
        cls.oudbehandelaren_object = OudbehandelarenObjectFactory()
        cls.user = UserFactory.create(
            username=cls.oudbehandelaren_object["record"]["data"]["oudbehandelaren"][0][
                "identificatie"
            ],
        )

    def test_retrieve_oudbehandelaren_not_logged_in(self, m):
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 403)

    def test_retrieve_oudbehandelaren_logged_in_no_permissions(self, m):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 403)

    def test_retrieve_oudbehandelaren_logged_in_permissions_for_other_zaaktype(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(self.user)
        with patch(
            "zac.contrib.objects.oudbehandelaren.api.views.find_zaak",
            return_value=factory(Zaak, self.zaak),
        ):
            with patch(
                "zac.contrib.objects.oudbehandelaren.api.views.fetch_oudbehandelaren",
                return_value=factory(
                    Oudbehandelaren, self.oudbehandelaren_object["record"]["data"]
                ),
            ):
                response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 403)

    def test_retrieve_oudbehandelaren_logged_in_with_blueprint_permissions(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": self.zaaktype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(self.user)
        with patch(
            "zac.contrib.objects.oudbehandelaren.api.views.find_zaak",
            return_value=factory(Zaak, self.zaak),
        ):
            with patch(
                "zac.contrib.objects.oudbehandelaren.api.views.fetch_oudbehandelaren",
                return_value=factory(
                    Oudbehandelaren, self.oudbehandelaren_object["record"]["data"]
                ),
            ):
                response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)

    def test_retrieve_oudbehandelaren_logged_in_with_atomic_permissions(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        AtomicPermissionFactory.create(
            for_user=self.user,
            permission=zaken_inzien.name,
            object_url=self.zaak["url"],
        )
        self.client.force_authenticate(self.user)
        with patch(
            "zac.contrib.objects.oudbehandelaren.api.views.find_zaak",
            return_value=factory(Zaak, self.zaak),
        ):
            with patch(
                "zac.contrib.objects.oudbehandelaren.api.views.fetch_oudbehandelaren",
                return_value=factory(
                    Oudbehandelaren, self.oudbehandelaren_object["record"]["data"]
                ),
            ):
                response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
