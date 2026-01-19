from unittest.mock import patch

from django.conf import settings
from django.urls import reverse

import requests_mock
from elasticsearch_dsl import Index
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes

from zac.accounts.tests.factories import (
    AccessRequestFactory,
    BlueprintPermissionFactory,
    GroupFactory,
    UserFactory,
)
from zac.activities.tests.factories import ActivityFactory, EventFactory
from zac.camunda.constants import AssigneeTypeChoices
from zac.contrib.objects.checklists.tests.factories import CATALOGI_ROOT, ZAKEN_ROOT
from zac.contrib.objects.kownsl.tests.factories import CATALOGI_ROOT, ZAKEN_ROOT
from zac.core.permissions import zaken_handle_access, zaken_inzien
from zac.core.rollen import Rol
from zac.core.tests.utils import ClearCachesMixin, mock_parallel
from zac.elasticsearch.api import create_rol_document
from zac.elasticsearch.documents import ZaakDocument, ZaakTypeDocument
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests import ServiceFactory

from ..data import ActivityGroup

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"


@requests_mock.Mocker()
class SummaryTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    """
    Test the access requests API endpoint.

    """

    endpoint = reverse(
        "werkvoorraad:summary",
    )

    def setUp(self):
        super().setUp()
        patchers = [
            patch("zac.werkvoorraad.views.parallel", return_value=mock_parallel()),
            patch(
                "zac.werkvoorraad.views.get_camunda_user_task_count",
                return_value=1,
            ),
            patch(
                "zac.werkvoorraad.views.count_review_requests_by_user",
                return_value=4,
            ),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_summary_no_permission(self, m):
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 403)

    def test_summary_permission(self, m):
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        user = UserFactory.create()
        group_1 = GroupFactory.create()
        user.groups.add(group_1)
        user.save()
        self.client.force_authenticate(user=user)

        zaaktype_document1 = ZaakTypeDocument(
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            catalogus_domein="DOME",
            catalogus=f"{CATALOGI_ROOT}catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            omschrijving="zaaktype1",
            identificatie="id1",
        )
        zaak_document1 = ZaakDocument(
            meta={"id": "a522d30c-6c10-47fe-82e3-e9f524c14ca8"},
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zaaktype_document1,
            identificatie="ZAAK1",
            bronorganisatie="123456",
            omschrijving="Some zaak description",
            vertrouwelijkheidaanduiding="beperkt_openbaar",
            va_order=16,
            rollen=[
                {
                    "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
                    "betrokkene_type": "organisatorische_eenheid",
                    "betrokkene_identificatie": {
                        "identificatie": "123456",
                    },
                },
                {
                    "url": f"{ZAKEN_ROOT}rollen/de7039d7-242a-4186-91c3-c3b49228211a",
                    "betrokkene_type": "medewerker",
                    "omschrijving_generiek": "behandelaar",
                    "betrokkene_identificatie": {
                        "identificatie": f"{AssigneeTypeChoices.user}:some_username",
                    },
                },
            ],
            eigenschappen=dict(),
            startdatum="2021-12-01",
            registratiedatum="2021-12-01",
            deadline="2021-12-31",
        )
        zaak_document1.save()
        zaken = Index(settings.ES_INDEX_ZAKEN)
        zaken.refresh()

        rol_1 = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": zaak_document1.url,
            "betrokkene": None,
            "betrokkeneType": "medewerker",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": f"{AssigneeTypeChoices.user}:{user}",
            },
        }
        rol = create_rol_document(factory(Rol, rol_1))
        zaak_document1.rollen = [rol]
        zaak_document1.save()
        zaken.refresh()

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_handle_access.name],
            for_user=user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "zaaktype1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "zaaktype1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        AccessRequestFactory.create(zaak=zaak_document1.url)
        AccessRequestFactory.create()

        user_activity = ActivityFactory.create(
            zaak=zaak_document1.url, user_assignee=user
        )
        ActivityGroup(
            activities=[user_activity],
            zaak=None,
            zaak_url=zaak_document1.url,
        )
        EventFactory.create(activity=user_activity)

        group_activity = ActivityFactory.create(
            zaak=zaak_document1.url, group_assignee=group_1
        )
        ActivityGroup(
            activities=[group_activity],
            zaak=None,
            zaak_url=zaak_document1.url,
        )
        EventFactory.create(activity=group_activity)

        response = self.client.post(self.endpoint)
        self.assertEqual(
            response.json(),
            {
                "userTasks": 1,
                "groupTasks": 1,
                "zaken": 1,
                "reviews": 4,
                "userActivities": 1,
                "groupActivities": 1,
                "accessRequests": 1,
            },
        )

        # No review requests
        with self.subTest("Test no review requests"):
            with patch(
                "zac.werkvoorraad.views.count_review_requests_by_user",
                return_value=None,
            ):
                resp = self.client.post(self.endpoint)
                self.assertEqual(
                    resp.json(),
                    {
                        "userTasks": 1,
                        "groupTasks": 1,
                        "zaken": 1,
                        "reviews": 0,
                        "userActivities": 1,
                        "groupActivities": 1,
                        "accessRequests": 1,
                    },
                )
