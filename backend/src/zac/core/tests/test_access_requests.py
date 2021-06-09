from datetime import date

from django.core import mail
from django.test import TestCase
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _

import requests_mock
from django_webtest import TransactionWebTest
from freezegun import freeze_time
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.constants import AccessRequestResult
from zac.accounts.models import AccessRequest, AtomicPermission
from zac.accounts.tests.factories import (
    AccessRequestFactory,
    BlueprintPermissionFactory,
    UserFactory,
)
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import paginated_response
from zgw.models import Zaak

from ..permissions import zaken_handle_access, zaken_request_access
from .utils import ClearCachesMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"

BRONORGANISATIE = "123456782"
IDENTIFICATIE = "ZAAK-001"


@requests_mock.Mocker()
class CreateAccessRequestTests(ESMixin, ClearCachesMixin, TransactionWebTest):
    url = reverse_lazy(
        "core:access-request-create",
        kwargs={
            "bronorganisatie": BRONORGANISATIE,
            "identificatie": IDENTIFICATIE,
        },
    )

    def setUp(self):
        super().setUp()

        self.user = UserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        self.app.set_user(self.user)

    def _setUpMocks(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        self.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/c25a4e4b-c19c-4ab9-a51b-1e9a65890383",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
        )
        self.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            identificatie="ZT1",
            catalogus=f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d",
            omschrijving="ZT1",
        )
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={BRONORGANISATIE}&identificatie={IDENTIFICATIE}",
            json=paginated_response([self.zaak]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            json=self.zaaktype,
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )

    def test_display_form_no_perms(self, m):
        self._setUpMocks(m)

        response = self.app.get(self.url, status=403)

        self.assertEqual(response.status_code, 403)

    def test_create_success(self, m):
        self._setUpMocks(m)
        handler = UserFactory.create()
        BlueprintPermissionFactory.create(
            permission=zaken_request_access.name,
            for_user=self.user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        # can't use generate_oas_component because of polymorphism
        rol = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": self.zaak["url"],
            "betrokkene": None,
            "betrokkeneType": "medewerker",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": handler.username,
            },
        }
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([rol]),
        )

        get_response = self.app.get(self.url)

        form = get_response.forms[1]
        form["comment"] = "some comment"

        response = form.submit()

        self.assertEqual(response.status_code, 302)

        access_request = AccessRequest.objects.get()

        self.assertEqual(access_request.requester, self.user)
        self.assertEqual(access_request.zaak, self.zaak["url"])
        self.assertEqual(access_request.comment, "some comment")

    def test_create_fail_other_access_request(self, m):
        self._setUpMocks(m)
        handler = UserFactory.create()
        BlueprintPermissionFactory.create(
            permission=zaken_request_access.name,
            for_user=self.user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        # can't use generate_oas_component because of polymorphism
        rol = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": self.zaak["url"],
            "betrokkene": None,
            "betrokkeneType": "medewerker",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": handler.username,
            },
        }
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([rol]),
        )
        previous_request = AccessRequestFactory.create(
            requester=self.user, zaak=self.zaak["url"]
        )

        get_response = self.app.get(self.url)

        form = get_response.forms[1]
        form["comment"] = "some comment"

        response = form.submit()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.html.find(class_="input__error").text,
            _("You've already requested access for this zaak"),
        )

        self.assertEqual(
            AccessRequest.objects.exclude(id=previous_request.id).count(), 0
        )


class CreateAccessRequestPermissionTests(ClearCachesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            identificatie="ZT1",
            catalogus=f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d",
            omschrijving="ZT1",
        )
        cls.zaaktype_model = factory(ZaakType, cls.zaaktype)
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/c25a4e4b-c19c-4ab9-a51b-1e9a65890383",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
        )
        cls.zaak_model = factory(Zaak, cls.zaak)
        cls.zaak_model.zaaktype = cls.zaaktype_model

    def test_user_has_no_permission_at_all(self):
        user = UserFactory.create()

        result = user.has_perm(zaken_request_access.name, self.zaak_model)

        self.assertFalse(result)

    @requests_mock.Mocker()
    def test_user_has_other_permission(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            permission=zaken_request_access.name,
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        result = user.has_perm(zaken_request_access.name, self.zaak_model)

        self.assertFalse(result)

    @requests_mock.Mocker()
    def test_has_permission_without_oo_restriction(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            permission=zaken_request_access.name,
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        result = user.has_perm(zaken_request_access.name, self.zaak_model)

        self.assertTrue(result)


@freeze_time("2020-01-01")
@requests_mock.Mocker()
class HandleAccessRequestsTests(ESMixin, TransactionWebTest):
    url = reverse_lazy(
        "core:zaak-access-requests",
        kwargs={
            "bronorganisatie": BRONORGANISATIE,
            "identificatie": IDENTIFICATIE,
        },
    )

    def setUp(self):
        super().setUp()

        self.user = UserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        self.app.set_user(self.user)

    def _setUpMocks(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        self.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/c25a4e4b-c19c-4ab9-a51b-1e9a65890383",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
        )
        m.get(self.zaak["url"], json=self.zaak)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={BRONORGANISATIE}&identificatie={IDENTIFICATIE}",
            json=paginated_response([self.zaak]),
        )
        self.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            catalogus=f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d",
            identificatie="ZT1",
            omschrijving="ZT1",
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            json=self.zaaktype,
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        # can't use generate_oas_component because of polymorphism
        self.rol = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": self.zaak["url"],
            "betrokkene": None,
            "betrokkeneType": "medewerker",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": self.user.username,
            },
        }

    def test_read_access_requests_no_perms(self, m):
        self._setUpMocks(m)
        AccessRequestFactory.create_batch(2, zaak=self.zaak["url"])

        response = self.app.get(self.url, status=403)

        self.assertEqual(response.status_code, 403)

    def test_read_access_request_not_behandelaar(self, m):
        self._setUpMocks(m)
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )

        AccessRequestFactory.create_batch(2, zaak=self.zaak["url"])
        BlueprintPermissionFactory.create(
            permission=zaken_handle_access.name,
            for_user=self.user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.app.get(self.url, status=403)

        self.assertEqual(response.status_code, 403)

    def test_read_access_requests_have_perms(self, m):
        self._setUpMocks(m)
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([self.rol]),
        )

        AccessRequestFactory.create_batch(2, zaak=self.zaak["url"])
        BlueprintPermissionFactory.create(
            permission=zaken_handle_access.name,
            for_user=self.user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.app.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_approve_access_requests(self, m):
        self._setUpMocks(m)
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([self.rol]),
        )

        AccessRequestFactory.create_batch(2, zaak=self.zaak["url"])
        BlueprintPermissionFactory.create(
            permission=zaken_handle_access.name,
            for_user=self.user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        get_response = self.app.get(self.url)

        form = get_response.forms[1]
        form["form-0-checked"].checked = True
        form["form-0-end_date"] = "2020-12-12"
        form["form-1-end_date"] = "2020-11-11"

        response = form.submit("submit", value="approve")

        self.assertEqual(response.status_code, 302)

        approved_request = AccessRequest.objects.get(id=int(form["form-0-id"].value))
        self.assertEqual(approved_request.result, AccessRequestResult.approve)
        self.assertEqual(approved_request.handled_date, date(2020, 1, 1))

        other_request = AccessRequest.objects.get(id=int(form["form-1-id"].value))
        self.assertEqual(other_request.result, "")
        self.assertIsNone(other_request.handled_date)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        subject = _("Access Request to %(zaak)s") % {"zaak": IDENTIFICATIE}
        self.assertEqual(email.subject, subject)
        self.assertEqual(email.to, [approved_request.requester.email])

        zaak_detail_path = reverse(
            "core:zaak-detail",
            kwargs={
                "bronorganisatie": BRONORGANISATIE,
                "identificatie": IDENTIFICATIE,
            },
        )
        url = f"http://testserver{zaak_detail_path}"
        self.assertIn(url, email.body)

        atomic_permission = AtomicPermission.objects.for_user(
            approved_request.requester
        ).get()
        self.assertEqual(atomic_permission.object_url, approved_request.zaak)

    def test_approve_access_requests_without_end_date_fail(self, m):
        self._setUpMocks(m)
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([self.rol]),
        )

        AccessRequestFactory.create_batch(2, zaak=self.zaak["url"])
        BlueprintPermissionFactory.create(
            permission=zaken_handle_access.name,
            for_user=self.user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        get_response = self.app.get(self.url)

        form = get_response.forms[1]
        form["form-0-checked"].checked = True

        response = form.submit("submit", value="approve")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.html.find(class_="input__error").text,
            _("End date of the access must be specified"),
        )

    def test_reject_access_requests(self, m):
        self._setUpMocks(m)
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([self.rol]),
        )

        AccessRequestFactory.create_batch(2, zaak=self.zaak["url"])
        BlueprintPermissionFactory.create(
            permission=zaken_handle_access.name,
            for_user=self.user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        get_response = self.app.get(self.url)

        form = get_response.forms[1]
        form["form-0-checked"].checked = True

        response = form.submit("submit", value="reject")

        self.assertEqual(response.status_code, 302)

        rejected_request = AccessRequest.objects.get(id=int(form["form-0-id"].value))
        self.assertEqual(rejected_request.result, AccessRequestResult.reject)

        other_request = AccessRequest.objects.get(id=int(form["form-1-id"].value))
        self.assertEqual(other_request.result, "")

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        subject = _("Access Request to %(zaak)s") % {"zaak": IDENTIFICATIE}
        self.assertEqual(email.subject, subject)
        self.assertEqual(email.to, [rejected_request.requester.email])
