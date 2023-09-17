from unittest.mock import patch

from django.contrib.sites.models import Site
from django.core import mail
from django.core.management import call_command
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _

import requests_mock
from freezegun import freeze_time
from rest_framework.test import APITestCase
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import UserFactory
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.tests.utils import ClearCachesMixin, mock_parallel
from zac.tests.utils import mock_resource_get

from .utils import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    CHECKLIST_OBJECT,
    CHECKLIST_OBJECTTYPE,
    CHECKLISTTYPE_OBJECT,
    CHECKLISTTYPE_OBJECTTYPE,
    IDENTIFICATIE,
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    ZAAK_URL,
    ZAKEN_ROOT,
)


@requests_mock.Mocker()
@freeze_time("1999-12-31T23:59:59Z")
class UnlockChecklists(ClearCachesMixin, APITestCase):
    endpoint = reverse_lazy(
        "unlock-checklists",
    )

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
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
        meta_config.checklisttype_objecttype = CHECKLISTTYPE_OBJECTTYPE["url"]
        meta_config.checklist_objecttype = CHECKLIST_OBJECTTYPE["url"]
        meta_config.save()

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
        cls.patchers = [
            patch(
                "zac.contrib.objects.checklists.management.commands.unlock_checklists.parallel",
                return_value=mock_parallel(),
            )
        ]

    def setUp(self):
        super().setUp()
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_command_unlock_checklists_did_not_find_user(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        self.client.force_authenticate(user=self.user)

        with patch(
            "zac.contrib.objects.checklists.management.commands.unlock_checklists.fetch_all_locked_checklists",
            return_value=[CHECKLIST_OBJECT],
        ):
            with patch(
                "zac.contrib.objects.services.fetch_checklisttype_object",
                return_value=[CHECKLISTTYPE_OBJECT],
            ):
                with patch(
                    "zac.contrib.objects.checklists.management.commands.unlock_checklists.logger"
                ) as mock_logger:
                    call_command("unlock_checklists")

        mock_logger.warning("User %s can't be found.", None)
        mock_logger.info.assert_called_once_with("0 checklists were unlocked.")

        # test email
        self.assertEqual(len(mail.outbox), 0)

    def test_command_unlock_checklists_found_user(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        self.client.force_authenticate(user=self.user)

        with patch(
            "zac.contrib.objects.checklists.management.commands.unlock_checklists.fetch_all_locked_checklists",
            return_value=[
                {
                    **CHECKLIST_OBJECT,
                    "record": {
                        **CHECKLIST_OBJECT["record"],
                        "data": {
                            **CHECKLIST_OBJECT["record"]["data"],
                            "lockedBy": self.user.username,
                        },
                    },
                }
            ],
        ):
            with patch(
                "zac.contrib.objects.services.fetch_checklisttype_object",
                return_value=[CHECKLISTTYPE_OBJECT],
            ):
                with patch(
                    "zac.contrib.objects.checklists.management.commands.unlock_checklists.logger"
                ) as mock_logger:
                    call_command("unlock_checklists")

        mock_logger.info.assert_called_once_with("1 checklists were unlocked.")

        # test email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        subject = _("Checklist of zaak: `%(zaak)s` unlocked.") % {"zaak": IDENTIFICATIE}
        self.assertEqual(email.subject, subject)
        self.assertEqual(email.to, [self.user.email])

        zaak_detail_path = f"/ui/zaken/{BRONORGANISATIE}/{IDENTIFICATIE}"
        url = f"http://testserver{zaak_detail_path}"
        self.assertIn(url, email.body)

    def test_endpoint_unlock_checklists(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        self.client.force_authenticate(user=self.user)

        with patch(
            "zac.contrib.objects.checklists.management.commands.unlock_checklists.fetch_all_locked_checklists",
            return_value=[
                {
                    **CHECKLIST_OBJECT,
                    "record": {
                        **CHECKLIST_OBJECT["record"],
                        "data": {
                            **CHECKLIST_OBJECT["record"]["data"],
                            "lockedBy": self.user.username,
                        },
                    },
                }
            ],
        ):
            with patch(
                "zac.contrib.objects.services.fetch_checklisttype_object",
                return_value=[CHECKLISTTYPE_OBJECT],
            ):
                response = self.client.post(self.endpoint)

        self.assertEqual(response.json(), {"count": 1})

        # test email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        subject = _("Checklist of zaak: `%(zaak)s` unlocked.") % {"zaak": IDENTIFICATIE}
        self.assertEqual(email.subject, subject)
        self.assertEqual(email.to, [self.user.email])

        zaak_detail_path = f"/ui/zaken/{BRONORGANISATIE}/{IDENTIFICATIE}"
        url = f"http://testserver{zaak_detail_path}"
        self.assertIn(url, email.body)
