from unittest.mock import patch

from django.urls import reverse_lazy

import requests_mock
from freezegun import freeze_time
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import SuperUserFactory
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import paginated_response
from zgw.models import Zaak

from .factories import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    IDENTIFICATIE,
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    ZAAK_URL,
    OudbehandelarenObjectFactory,
    OudbehandelarenObjectTypeFactory,
)

OUDBEHANDELAREN_OBJECTTYPE = OudbehandelarenObjectTypeFactory()


@requests_mock.Mocker()
class ApiResponseTests(ClearCachesMixin, APITestCase):
    endpoint = reverse_lazy(
        "zaak-oudbehandelaren",
        kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE},
    )

    @classmethod
    def setUpTestData(cls):
        cls.maxDiff = None
        super().setUpTestData()

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
        cls.user = SuperUserFactory.create(
            is_staff=True,
            username=cls.oudbehandelaren_object["record"]["data"]["oudbehandelaren"][0][
                "identificatie"
            ].split(":")[-1],
        )

    def test_retrieve_oudbehandelaren(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=100",
            json=paginated_response([self.oudbehandelaren_object]),
        )
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([OUDBEHANDELAREN_OBJECTTYPE]),
        )
        self.client.force_authenticate(user=self.user)
        with patch(
            "zac.contrib.objects.oudbehandelaren.api.views.find_zaak",
            return_value=factory(Zaak, self.zaak),
        ):
            response = self.client.get(self.endpoint)

        self.assertEqual(
            response.json(),
            {
                "zaak": "https://open-zaak.nl/zaken/api/v1/zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
                "oudbehandelaren": [
                    {
                        "email": "some-email@email.com",
                        "ended": "2023-01-01T00:00:00Z",
                        "started": "2023-01-02T00:00:00Z",
                        "user": {
                            "id": self.user.id,
                            "username": self.user.username,
                            "firstName": "",
                            "fullName": self.user.username,
                            "lastName": "",
                            "isStaff": True,
                            "email": self.user.email,
                            "groups": [],
                        },
                        "changer": {
                            "id": self.user.id,
                            "username": self.user.username,
                            "firstName": "",
                            "fullName": self.user.username,
                            "lastName": "",
                            "isStaff": True,
                            "email": self.user.email,
                            "groups": [],
                        },
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_retrieve_checklist_404(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.post(
            f"{OBJECTS_ROOT}objects/search?pageSize=100",
            json=paginated_response([]),
        )
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([OUDBEHANDELAREN_OBJECTTYPE]),
        )
        self.client.force_authenticate(user=self.user)
        with patch(
            "zac.contrib.objects.oudbehandelaren.api.views.find_zaak",
            return_value=factory(Zaak, self.zaak),
        ):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, 404)
