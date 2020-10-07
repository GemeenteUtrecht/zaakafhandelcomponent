import contextlib
import datetime
from unittest.mock import patch

from django.conf import settings
from django.urls import reverse, reverse_lazy

import requests_mock
from django_webtest import TransactionWebTest
from freezegun import freeze_time
from rest_framework import status
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.constants import AccessRequestResult
from zac.accounts.tests.factories import (
    AccessRequestFactory,
    PermissionSetFactory,
    UserFactory,
)
from zac.contrib.kownsl.data import Approval, ReviewRequest
from zac.tests.utils import (
    generate_oas_component,
    make_document_objects,
    mock_service_oas_get,
    paginated_response,
)

from ..permissions import (
    zaakproces_send_message,
    zaakproces_usertasks,
    zaken_inzien,
    zaken_request_access,
)
from .mocks import get_camunda_task_mock
from .utils import ClearCachesMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"
DOCUMENTEN_ROOT = "https://api.documenten.nl/api/v1/"

BRONORGANISATIE = "123456782"
IDENTIFICATIE = "ZAAK-001"


@contextlib.contextmanager
def mock_zaak_detail_context(documents=None):
    review_request_data = {
        "id": "45638aa6-e177-46cc-b580-43339795d5b5",
        "for_zaak": f"{ZAKEN_ROOT}zaak/123",
        "review_type": "approval",
        "documents": [],
        "frontend_url": f"https://kownsl.nl/45638aa6-e177-46cc-b580-43339795d5b5",
        "num_advices": 0,
        "num_approvals": 1,
        "num_assigned_users": 1,
        "toelichting": "",
    }
    approval_data = {
        "created": datetime.datetime(2020, 1, 1, 12, 00, 1),
        "author": {
            "username": "test_reviewer",
            "first_name": "",
            "last_name": "",
        },
        "approved": False,
        "toelichting": "",
    }
    review_request = factory(ReviewRequest, review_request_data)
    approval = factory(Approval, approval_data)

    m_get_statussen = patch("zac.core.views.zaken.get_statussen", return_value=[])
    m_get_statussen.start()
    if documents is None:
        returned_documents = []
    else:
        returned_documents = documents
    m_get_documenten = patch(
        "zac.core.views.zaken.get_documenten", return_value=(returned_documents, [])
    )
    m_get_documenten.start()
    m_get_zaak_eigenschappen = patch(
        "zac.core.views.zaken.get_zaak_eigenschappen", return_value=[]
    )
    m_get_zaak_eigenschappen.start()
    m_get_related_zaken = patch(
        "zac.core.views.zaken.get_related_zaken", return_value=[]
    )
    m_get_related_zaken.start()
    m_get_resultaat = patch("zac.core.views.zaken.get_resultaat", return_value=None)
    m_get_resultaat.start()
    m_get_rollen = patch("zac.core.views.zaken.get_rollen", return_value=[])
    m_get_rollen.start()
    m_retrieve_advices = patch("zac.core.views.zaken.retrieve_advices", return_value=[])
    m_retrieve_advices.start()
    m_retrieve_approvals = patch(
        "zac.core.views.zaken.retrieve_approvals", return_value=[approval]
    )
    m_retrieve_approvals.start()
    m_get_review_requests = patch(
        "zac.core.views.zaken.get_review_requests", return_value=[review_request]
    )
    m_get_review_requests.start()
    yield
    m_get_statussen.stop()
    m_get_documenten.stop()
    m_get_zaak_eigenschappen.stop()
    m_get_related_zaken.stop()
    m_get_resultaat.stop()
    m_get_rollen.stop()
    m_retrieve_advices.stop()
    m_retrieve_approvals.stop()
    m_get_review_requests.stop()


@requests_mock.Mocker()
class ZaakDetailTests(ClearCachesMixin, TransactionWebTest):

    url = reverse_lazy(
        "core:zaak-detail",
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

        self.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            identificatie="ZT1",
            catalogus=f"{CATALOGI_ROOT}catalogi/2fa14cce-12d0-4f57-8d5d-ecbdfbe06a5e",
        )
        self.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=self.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )

    def _setUpMocks(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
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

    def test_login_required(self, m):
        response = self.app.get(self.url)

        self.assertRedirects(response, f"{settings.LOGIN_URL}?next={self.url}")

    def test_user_auth_no_perms(self, m):
        self._setUpMocks(m)

        response = self.app.get(self.url, user=self.user, status=403)

        self.assertEqual(response.status_code, 403)
        # no url to request access
        self.assertIsNone(response.html.find(class_="main__content").find("p"))

    def test_user_auth_no_perms_can_request(self, m):
        self._setUpMocks(m)
        PermissionSetFactory.create(
            permissions=[zaken_request_access.name],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )

        with patch("zac.core.rules.test_oo_allowlist", return_value=True):
            response = self.app.get(self.url, user=self.user, status=403)

        self.assertEqual(response.status_code, 403)
        # show url to request access
        self.assertEqual(
            response.html.find(class_="main__content").find("p").text.strip(),
            "You can request access for this page",
        )

    def test_user_has_perm_but_not_for_zaaktype(self, m):
        self._setUpMocks(m)

        # gives them access to the page, but no catalogus specified -> nothing visible
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus="",
            zaaktype_identificaties=[],
            max_va=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )

        response = self.app.get(self.url, user=self.user, status=403)

        self.assertEqual(response.status_code, 403)

    def test_user_has_perm_but_not_for_va(self, m):
        self._setUpMocks(m)

        # gives them access to the page and zaaktype, but insufficient VA
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.openbaar,
        )

        response = self.app.get(self.url, user=self.user, status=403)

        self.assertEqual(response.status_code, 403)

    def test_user_has_perm(self, m):
        self._setUpMocks(m)

        # gives them access to the page, zaaktype and VA specified -> visible
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )

        # mock out all the other calls - we're testing auth here
        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

    def test_user_has_all_zaaktype_perms(self, m):
        self._setUpMocks(m)

        # gives them access to the page, catalogus and VA specified -> all zaaktypen visible
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=[],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )

        # mock out all the other calls - we're testing auth here
        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

    @freeze_time("2020-01-02 12:00:01")
    def test_approval_case_details(self, m):
        self._setUpMocks(m)

        # gives them access to the page, zaaktype and VA specified -> visible
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )
        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

    def test_user_has_temp_auth(self, m):
        self._setUpMocks(m)

        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus="",
            zaaktype_identificaties=[],
            max_va=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        AccessRequestFactory.create(
            requester=self.user,
            zaak=self.zaak["url"],
            result=AccessRequestResult.approve,
            end_date=datetime.date.today(),
        )

        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

    def test_user_has_temp_auth_expired(self, m):
        self._setUpMocks(m)

        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus="",
            zaaktype_identificaties=[],
            max_va=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        AccessRequestFactory.create(
            requester=self.user,
            zaak=self.zaak["url"],
            result=AccessRequestResult.approve,
            end_date=datetime.date.today() - datetime.timedelta(days=1),
        )

        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user, status=403)

        self.assertEqual(response.status_code, 403)


@requests_mock.Mocker()
class ZaakDetailsDocumentenTests(ClearCachesMixin, TransactionWebTest):

    zaak_detail_url = reverse_lazy(
        "core:zaak-detail",
        kwargs={
            "bronorganisatie": BRONORGANISATIE,
            "identificatie": IDENTIFICATIE,
        },
    )

    zaak_data = {
        "bronorganisatie": "123456782",
        "identificatie": "ZAAK-001",
        "zaaktype": f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
        "url": f"{ZAKEN_ROOT}zaken/2fc7a200-3262-483e-8235-a5f3d551f547",
        "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.openbaar,
    }
    zaaktype_data = {
        "url": f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
        "identificatie": "ZT1",
        "omschrijving": "QpCMmqhZBUGXliSZSgbhxKfEQYOGGLnkGdtokEJXhOC",
        "vertrouwelijkheidaanduiding": "openbaar",
        "catalogus": f"{CATALOGI_ROOT}catalogussen/4bf4d9e1-65f6-45a9-a008-f402de922b33",
    }

    document_1 = {
        "url": f"{DOCUMENTEN_ROOT}enkelvoudiginformatieobjecten/efd772a2-782d-48a6-bbb4-970c8aecc78d",
        "titel": "Test Document 1",
        "informatieobjecttype": f"{CATALOGI_ROOT}informatieobjecttypen/c055908a-242b-469d-aead-8b838dc4ac7a",
    }

    document_2 = {
        "url": f"{DOCUMENTEN_ROOT}enkelvoudiginformatieobjecten/9510addc-e396-442e-b76b-02705e45bb16",
        "titel": "Test Document 2",
        "informatieobjecttype": f"{CATALOGI_ROOT}informatieobjecttypen/10481de9-fdfd-4ce5-9d4b-10e844460d7d",
    }

    zio_1 = {
        "url": f"{ZAKEN_ROOT}zaakinformatieobjecten/e33e6b35-4b36-4619-9234-490459383a19",
        "zaak": zaak_data["url"],
        "informatieobject": document_1["url"],
    }

    zio_2 = {
        "url": f"{ZAKEN_ROOT}zaakinformatieobjecten/e33e6b35-4b36-4619-9234-490459383a19",
        "zaak": zaak_data["url"],
        "informatieobject": document_2["url"],
    }

    iot_1 = {
        "url": document_1["informatieobjecttype"],
        "catalogus": f"{CATALOGI_ROOT}catalogussen/1b817d02-09dc-4e5f-9c98-cc9a991b81c6",
        "omschrijving": "Test Omschrijving 1",
        "vertrouwelijkheidaanduiding": "openbaar",
    }

    iot_2 = {
        "url": document_2["informatieobjecttype"],
        "catalogus": f"{CATALOGI_ROOT}catalogussen/1b817d02-09dc-4e5f-9c98-cc9a991b81c6",
        "omschrijving": "Test Omschrijving 2",
        "vertrouwelijkheidaanduiding": "geheim",
    }

    def setUp(self):
        super().setUp()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTEN_ROOT)

        self.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
        )

        self.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
        )
        document_data = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )

        self.zaak.update(self.zaak_data)
        self.zaaktype.update(self.zaaktype_data)
        self.document_1 = {**document_data, **self.document_1}
        self.document_2 = {**document_data, **self.document_2}

    def _set_up_mocks(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={BRONORGANISATIE}&identificatie={IDENTIFICATIE}",
            json=paginated_response([self.zaak]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            json=self.zaaktype,
        )
        m.get(self.zaaktype["catalogus"])
        m.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={self.zaak['url']}",
            json=[self.zio_1, self.zio_2],
        )
        m.get(self.iot_1["catalogus"])

    def test_no_catalogus_no_documents_shown(self, m):
        self._set_up_mocks(m)

        user = UserFactory.create()

        # No informatieobjecttype_catalogus in the permission
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )

        with mock_zaak_detail_context(
            documents=make_document_objects(
                [self.document_1, self.document_2], [self.iot_1, self.iot_2]
            )
        ):
            response = self.app.get(self.zaak_detail_url, user=user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("Test Document 1", response.html.text)
        self.assertNotIn("Test Document 2", response.html.text)

    def test_catalogus_but_no_informatieobjecttype(self, m):
        """Test that all the informatieobjecttypes within the catalogus are allowed"""
        self._set_up_mocks(m)

        user = UserFactory.create()
        self.app.set_user(user)

        # informatieobjecttype_catalogus in the permission, without informatieobjecttype_omschriving
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            informatieobjecttype_catalogus=self.iot_1[
                "catalogus"
            ],  # Same catalogus as iot_2
            informatieobjecttype_max_va=VertrouwelijkheidsAanduidingen.geheim,
        )

        with mock_zaak_detail_context(
            documents=make_document_objects(
                [self.document_1, self.document_2], [self.iot_1, self.iot_2]
            )
        ):
            response = self.app.get(self.zaak_detail_url, user=user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Test Document 1", response.html.text)
        self.assertIn("Test Document 2", response.html.text)

    def test_catalogus_with_va_but_no_informatieobjecttype(self, m):
        """
        Test that all the informatieobjecttypes within the catalogus are allowed, but the
        document with VA higher than that given in the permission set is not shown.
        """
        self._set_up_mocks(m)

        user = UserFactory.create()
        self.app.set_user(user)

        # informatieobjecttype_catalogus in the permission, without informatieobjecttype_omschriving
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            informatieobjecttype_catalogus=self.iot_1[
                "catalogus"
            ],  # Same catalogus as iot_2
            informatieobjecttype_max_va=VertrouwelijkheidsAanduidingen.openbaar,
        )

        with mock_zaak_detail_context(
            documents=make_document_objects(
                [self.document_1, self.document_2], [self.iot_1, self.iot_2]
            )
        ):
            response = self.app.get(self.zaak_detail_url, user=user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Test Document 1", response.html.text)
        self.assertNotIn("Test Document 2", response.html.text)

    def test_catalogus_and_informatieobjecttype_selected(self, m):
        """Test that the user sees only the allowed informatieobjecttypen"""
        self._set_up_mocks(m)

        user = UserFactory.create()
        self.app.set_user(user)

        # informatieobjecttype_omschriving is specified
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            informatieobjecttype_catalogus=self.iot_1[
                "catalogus"
            ],  # Same catalogus as iot_2
            informatieobjecttype_max_va=VertrouwelijkheidsAanduidingen.geheim,
            informatieobjecttype_omschrijvingen=["Test Omschrijving 1"],
        )

        with mock_zaak_detail_context(
            documents=make_document_objects(
                [self.document_1, self.document_2], [self.iot_1, self.iot_2]
            )
        ):
            response = self.app.get(self.zaak_detail_url, user=user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Test Document 1", response.html.text)
        self.assertNotIn("Test Document 2", response.html.text)


class ZaakProcessPermissionTests(ClearCachesMixin, TransactionWebTest):
    def setUp(self):
        super().setUp()

        self.user = UserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        self.mocker = requests_mock.Mocker()
        self.mocker.start()
        self.addCleanup(self.mocker.stop)
        self._setUpMocks()

    def _setUpMocks(self):
        m = self.mocker
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        self.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            catalogus=f"{CATALOGI_ROOT}catalogi/2fa14cce-12d0-4f57-8d5d-ecbdfbe06a5e",
            identificatie="ZT1",
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/5abd5f22-5317-4bf2-a750-7cf2f4910370",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=self.zaaktype["url"],
            status=None,
            relevanteAndereZaken=[],
        )
        m.get(zaak["url"], json=zaak)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={BRONORGANISATIE}&identificatie={IDENTIFICATIE}",
            json=paginated_response([zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [self.zaaktype],
            },
        )
        m.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={zaak['url']}",
            json=[],
        )
        m.get(
            f"{CATALOGI_ROOT}statustypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([]),
        )
        m.get(
            f"{ZAKEN_ROOT}statussen?zaak={zaak['url']}",
            json=paginated_response([]),
        )
        m.get(f"{zaak['url']}/zaakeigenschappen", json=[])

    def test_no_process_permissions(self):
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )

        url = reverse(
            "core:zaak-detail",
            kwargs={
                "bronorganisatie": BRONORGANISATIE,
                "identificatie": IDENTIFICATIE,
            },
        )
        self.app.set_user(self.user)
        with mock_zaak_detail_context():
            response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        react_div = response.pyquery(".process-interaction").eq(0)
        self.assertFalse(react_div)

    def test_process_permissions(self):
        PermissionSetFactory.create(
            permissions=[
                zaken_inzien.name,
                zaakproces_usertasks.name,
                zaakproces_send_message.name,
            ],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )

        url = reverse(
            "core:zaak-detail",
            kwargs={
                "bronorganisatie": BRONORGANISATIE,
                "identificatie": IDENTIFICATIE,
            },
        )
        self.app.set_user(self.user)

        with mock_zaak_detail_context():
            response = self.app.get(url)

        self.assertEqual(response.status_code, 200)

        react_div = response.pyquery(".process-interaction").eq(0)
        self.assertEqual(react_div.attr("data-can-do-usertasks"), "true")
        self.assertEqual(react_div.attr("data-can-send-bpmn-messages"), "true")

    def test_claim_task_no_permission(self):
        task = get_camunda_task_mock()
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/5abd5f22-5317-4bf2-a750-7cf2f4910371",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=self.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )
        self.mocker.get(
            f"https://camunda.example.com/engine-rest/task/{task['id']}",
            json=task,
        )
        self.mocker.get(
            f"https://camunda.example.com/engine-rest/process-instance/{task['process_instance_id']}",
            json={
                "id": task["process_instance_id"],
                "definitionId": "proces:1",
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
        )
        self.mocker.get(
            (
                f"https://camunda.example.com/engine-rest/process-instance/{task['process_instance_id']}"
                "/variables/zaakUrl?deserializeValues=false"
            ),
            json={
                "value": zaak["url"],
                "type": "String",
            },
        )
        self.mocker.get(zaak["url"], json=zaak)
        PermissionSetFactory.create(
            permissions=[
                zaken_inzien.name,
                zaakproces_usertasks.name,
            ],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.openbaar,
        )
        url = reverse("core:claim-task")

        with patch("zac.core.camunda.extract_task_form", return_value=None):
            self.client.force_login(self.user)
            response = self.client.post(
                url,
                {"task_id": task["id"], "zaak": zaak["url"]},
            )
        self.assertEqual(response.status_code, 403)

    def test_claim_task_with_permission(self):
        task = get_camunda_task_mock()
        zaak_url = f"{ZAKEN_ROOT}zaken/5abd5f22-5317-4bf2-a750-7cf2f4910370"
        PermissionSetFactory.create(
            permissions=[
                zaken_inzien.name,
                zaakproces_usertasks.name,
            ],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )

        url = reverse("core:claim-task")

        self.mocker.get(
            f"https://camunda.example.com/engine-rest/task/{task['id']}",
            json=task,
        )
        self.mocker.get(
            f"https://camunda.example.com/engine-rest/process-instance/{task['process_instance_id']}",
            json={
                "id": task["process_instance_id"],
                "definitionId": "proces:1",
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
        )
        self.mocker.get(
            (
                f"https://camunda.example.com/engine-rest/process-instance/{task['process_instance_id']}"
                "/variables/zaakUrl?deserializeValues=false"
            ),
            json={
                "value": zaak_url,
                "type": "String",
            },
        )

        with patch("zac.core.views.processes.get_client") as m_client, patch(
            "zac.core.camunda.extract_task_form",
            return_value=None,
        ), patch(
            "zac.core.views.processes.get_roltypen",
            return_value=[],
        ):
            self.client.force_login(self.user)
            response = self.client.post(
                url,
                {"task_id": task["id"], "zaak": zaak_url, "next": "/"},
            )

        self.assertEqual(response.status_code, 302)
        m_client.return_value.post.assert_called_once()
