from unittest.mock import patch

from django.urls import reverse

from freezegun import freeze_time
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component

from zac.accounts.tests.factories import UserFactory
from zgw.models.zrc import Zaak

from ..views import get_behandelaar_zaken_unfinished

ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"


class AssigneeCasesTests(APITestCase):
    """
    Test the assignee cases API endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory.create()
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
        )

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        zaak_unfinished = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            startdatum="2021-02-12",
            einddatum=None,
            einddatumGepland=None,
            uiterlijkeEinddatumAfdoening="2021-02-17",
        )
        cls.zaak_unfinished = factory(Zaak, zaak_unfinished)
        cls.zaak_unfinished.zaaktype = factory(ZaakType, cls.zaaktype)

        zaak_finished = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e39-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0011",
            bronorganisatie="123456782",
            startdatum="2021-02-12",
            einddatum="2021-02-14",
        )
        cls.zaak_finished = factory(Zaak, zaak_finished)

        cls.endpoint = reverse(
            "werkvoorraad:cases",
        )

    def setUp(self):
        super().setUp()

        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    def test_other_user_logging_in(self):
        self.client.logout()
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @freeze_time("2021-12-16T12:00:00Z")
    def test_get_unfinished_zaken(self):
        with patch(
            "zac.werkvoorraad.views.get_behandelaar_zaken",
            return_value=[self.zaak_finished, self.zaak_unfinished],
        ):
            unfinished_zaken = get_behandelaar_zaken_unfinished(self.user)

        self.assertEqual(len(unfinished_zaken), 1)
        self.assertTrue(self.zaak_unfinished in unfinished_zaken)

    def test_get_unfinished_zaken_no_zaken(self):
        with patch("zac.werkvoorraad.views.get_behandelaar_zaken", return_value=[]):
            unfinished_zaken = get_behandelaar_zaken_unfinished(self.user)

        self.assertEqual(len(unfinished_zaken), 0)

    def test_cases_endpoint(self):
        with patch(
            "zac.werkvoorraad.views.get_behandelaar_zaken",
            return_value=[self.zaak_finished, self.zaak_unfinished],
        ):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            {
                "bronorganisatie": self.zaak_unfinished.bronorganisatie,
                "einddatum": self.zaak_unfinished.einddatum,
                "einddatumGepland": self.zaak_unfinished.einddatum_gepland,
                "identificatie": self.zaak_unfinished.identificatie,
                "startdatum": str(self.zaak_unfinished.startdatum),
                "url": self.zaak_unfinished.url,
                "zaaktype": {
                    "url": self.zaaktype["url"],
                    "catalogus": self.zaaktype["catalogus"],
                    "omschrijving": self.zaaktype["omschrijving"],
                    "versiedatum": self.zaaktype["versiedatum"],
                },
                "omschrijving": self.zaak_unfinished.omschrijving,
                "toelichting": self.zaak_unfinished.toelichting,
                "registratiedatum": str(self.zaak_unfinished.registratiedatum),
                "uiterlijkeEinddatumAfdoening": str(
                    self.zaak_unfinished.uiterlijke_einddatum_afdoening
                ),
                "vertrouwelijkheidaanduiding": self.zaak_unfinished.vertrouwelijkheidaanduiding,
                "deadline": str(self.zaak_unfinished.deadline),
                "deadlineProgress": self.zaak_unfinished.deadline_progress(),
                "resultaat": None,
            },
            data[0],
        )
