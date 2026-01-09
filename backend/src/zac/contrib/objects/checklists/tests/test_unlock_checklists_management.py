from unittest.mock import patch

from django.contrib.sites.models import Site
from django.core import mail
from django.core.management import call_command
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

import requests_mock
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import UserFactory
from zac.contrib.objects.checklists.models import ChecklistLock
from zac.core.tests.utils import ClearCachesMixin, mock_parallel
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.mixins import FreezeTimeMixin
from zac.tests.utils import mock_resource_get

from .factories import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    IDENTIFICATIE,
    ZAAK_URL,
    ZAKEN_ROOT,
    ChecklistLockFactory,
)


@requests_mock.Mocker()
class UnlockChecklists(FreezeTimeMixin, ClearCachesMixin, APITestCase):
    frozen_time = "1999-12-31T23:59:59Z"
    endpoint = reverse_lazy(
        "unlock-checklists",
    )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )

        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
        )
        cls.user = UserFactory.create(is_staff=True)

        site = Site.objects.get_current()
        site.domain = "testserver"
        site.save()

    def setUp(self):
        super().setUp()
        patcher = patch(
            "zac.contrib.objects.checklists.management.commands.unlock_checklists.parallel",
            return_value=mock_parallel(),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_command_unlock_checklists(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        self.client.force_authenticate(user=self.user)
        ChecklistLockFactory.create(
            user=self.user, url="https://someurl.com/", zaak=self.zaak["url"]
        )

        with patch(
            "zac.contrib.objects.checklists.management.commands.unlock_checklists.logger"
        ) as mock_logger:
            call_command("unlock_checklists")

        mock_logger.info.assert_called_once_with("1 checklists were unlocked.")

        # test email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        subject = _(
            "Notification: Checklist of zaak %(zaak)s was automatically unlocked."
        ) % {"zaak": IDENTIFICATIE}
        self.assertEqual(email.subject, subject)
        self.assertEqual(email.to, [self.user.email])

        zaak_detail_path = f"/ui/zaken/{BRONORGANISATIE}/{IDENTIFICATIE}"
        url = f"http://testserver{zaak_detail_path}"
        self.assertIn(url, email.body)

    def test_endpoint_unlock_checklists(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        self.client.force_authenticate(user=self.user)
        ChecklistLockFactory.create(
            user=self.user, url="https://someurl.com/", zaak=self.zaak["url"]
        )
        response = self.client.post(self.endpoint)
        self.assertEqual(response.json(), {"count": 1})

        # test email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        subject = _(
            "Notification: Checklist of zaak %(zaak)s was automatically unlocked."
        ) % {"zaak": IDENTIFICATIE}
        self.assertEqual(email.subject, subject)
        self.assertEqual(email.to, [self.user.email])

        zaak_detail_path = f"/ui/zaken/{BRONORGANISATIE}/{IDENTIFICATIE}"
        url = f"http://testserver{zaak_detail_path}"
        self.assertIn(url, email.body)

        self.assertEqual(ChecklistLock.objects.all().count(), 0)
