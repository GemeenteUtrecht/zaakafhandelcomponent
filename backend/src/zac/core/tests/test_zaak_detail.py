import contextlib
import datetime
from unittest import skip
from unittest.mock import patch

from django.conf import settings
from django.urls import reverse, reverse_lazy
from django.utils import timezone

import requests_mock
from django_webtest import TransactionWebTest
from freezegun import freeze_time
from rest_framework import status
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.constants import PermissionObjectType
from zac.accounts.tests.factories import (
    PermissionDefinitionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.contrib.kownsl.data import Approval, ReviewRequest
from zac.contrib.kownsl.models import KownslConfig
from zac.contrib.organisatieonderdelen.tests.factories import (
    OrganisatieOnderdeelFactory,
)
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import make_document_objects, paginated_response

from ...accounts.models import InformatieobjecttypePermission
from ..permissions import (
    zaakproces_send_message,
    zaakproces_usertasks,
    zaken_download_documents,
    zaken_inzien,
    zaken_request_access,
)
from .mocks import get_camunda_task_mock
from .utils import ClearCachesMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"
DOCUMENTEN_ROOT = "https://api.documenten.nl/api/v1/"
KOWNSL_ROOT = "https://kownsl.nl/"

BRONORGANISATIE = "123456782"
IDENTIFICATIE = "ZAAK-001"


@contextlib.contextmanager
def mock_zaak_detail_context(documents=None):
    review_request_data = {
        "created": datetime.datetime(2020, 1, 1, 12, 00, 1),
        "id": "45638aa6-e177-46cc-b580-43339795d5b5",
        "for_zaak": f"{ZAKEN_ROOT}zaak/123",
        "review_type": "approval",
        "documents": [],
        "frontend_url": f"https://kownsl.nl/45638aa6-e177-46cc-b580-43339795d5b5",
        "num_advices": 0,
        "num_approvals": 1,
        "num_assigned_users": 1,
        "toelichting": "",
        "user_deadlines": {},
        "requester": "Henkie",
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
class ZaakDetailTests(ESMixin, ClearCachesMixin, TransactionWebTest):

    url = reverse_lazy(
        "core:zaak-detail",
        kwargs={
            "bronorganisatie": BRONORGANISATIE,
            "identificatie": IDENTIFICATIE,
        },
    )

    def setUp(self):
        super().setUp()

        self.user = UserFactory.create(username="testname")

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        kownsl = Service.objects.create(api_type=APITypes.orc, api_root=KOWNSL_ROOT)

        config = KownslConfig.get_solo()
        config.service = kownsl
        config.save()

        self.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            identificatie="ZT1",
            catalogus=f"{CATALOGI_ROOT}catalogi/2fa14cce-12d0-4f57-8d5d-ecbdfbe06a5e",
            omschrijving="ZT1",
        )
        self.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/99f3c444-d420-4a25-8dd1-03b6aaf1e132",
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

        PermissionDefinitionFactory.create(
            object_url="",
            permission=zaken_request_access.name,
            for_user=self.user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        with patch("zac.core.rules.test_oo_allowlist", return_value=True):
            response = self.app.get(self.url, user=self.user, status=403)

        self.assertEqual(response.status_code, 403)
        # show url to request access
        request_access_url = reverse(
            "core:access-request-create",
            kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE},
        )
        self.assertEqual(
            response.html.find(class_="main__content").find("p").find("a")["href"],
            request_access_url,
        )

    def test_user_has_perm_but_not_for_zaaktype(self, m):
        self._setUpMocks(m)

        # gives them access to the page, but no catalogus specified -> nothing visible
        PermissionDefinitionFactory.create(
            object_url="",
            permission=zaken_inzien.name,
            for_user=self.user,
            policy={
                "catalogus": "",
                "zaaktype_omschrijving": "",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )

        response = self.app.get(self.url, user=self.user, status=403)

        self.assertEqual(response.status_code, 403)

    def test_user_has_perm_but_not_for_va(self, m):
        self._setUpMocks(m)

        # gives them access to the page and zaaktype, but insufficient VA
        PermissionDefinitionFactory.create(
            object_url="",
            permission=zaken_inzien.name,
            for_user=self.user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )

        response = self.app.get(self.url, user=self.user, status=403)

        self.assertEqual(response.status_code, 403)

    def test_user_has_perm(self, m):
        self._setUpMocks(m)

        # gives them access to the page, zaaktype and VA specified -> visible
        PermissionDefinitionFactory.create(
            object_url="",
            permission=zaken_inzien.name,
            for_user=self.user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )

        # mock out all the other calls - we're testing auth here
        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

    @skip("Adding one permissions to all zaaktypen is deprecated")
    def test_user_has_all_zaaktype_perms(self, m):
        self._setUpMocks(m)

        # gives them access to the page, catalogus and VA specified -> all zaaktypen visible
        PermissionDefinitionFactory.create(
            object_url="",
            permission=zaken_inzien.name,
            for_user=self.user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )

        # mock out all the other calls - we're testing auth here
        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

    @freeze_time("2020-01-02 12:00:01")
    def test_approval_case_details(self, m):
        self._setUpMocks(m)

        # gives them access to the page, zaaktype and VA specified -> visible
        PermissionDefinitionFactory.create(
            object_url="",
            permission=zaken_inzien.name,
            for_user=self.user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

    def test_user_has_atomic_auth_with_no_end_date(self, m):
        self._setUpMocks(m)

        PermissionDefinitionFactory.create(
            object_url=self.zaak["url"],
            permission=zaken_inzien.name,
            for_user=self.user,
            end_date=None,
        )

        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

    def test_user_has_atomic_auth_expired(self, m):
        self._setUpMocks(m)

        PermissionDefinitionFactory.create(
            object_url=self.zaak["url"],
            permission=zaken_inzien.name,
            for_user=self.user,
            end_date=timezone.now() - datetime.timedelta(days=1),
        )

        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user, status=403)

        self.assertEqual(response.status_code, 403)

    @skip("for behandelaars atomic permissions are used now")
    def test_user_is_behandelaar(self, m):
        self._setUpMocks(m)
        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            betrokkeneType="medewerker",
            omschrijvingGeneriek="behandelaar",
            betrokkeneIdentificatie={
                "identificatie": self.user.username,
            },
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([rol]),
        )

        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

    @skip("for behandelaars atomic permissions are used now")
    def test_user_is_adviser(self, m):
        self._setUpMocks(m)
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        review_request = generate_oas_component(
            "kownsl",
            "schemas/ReviewRequest",
            id="1b864f55-0880-4207-9246-9b454cb69cca",
            forZaak=self.zaak["url"],
            userDeadlines={self.user.username: "2099-01-01"},
            metadata={},
            zaakDocuments={},
            reviews={},
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?for_zaak={self.zaak['url']}",
            json=[review_request],
        )

        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)


@requests_mock.Mocker()
class ZaakDetailsDocumentenTests(ESMixin, ClearCachesMixin, TransactionWebTest):

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
        "omschrijving": "ZT1",
        "vertrouwelijkheidaanduiding": "openbaar",
        "catalogus": f"{CATALOGI_ROOT}catalogussen/4bf4d9e1-65f6-45a9-a008-f402de922b33",
    }

    document_1 = {
        "url": f"{DOCUMENTEN_ROOT}enkelvoudiginformatieobjecten/efd772a2-782d-48a6-bbb4-970c8aecc78d",
        "titel": "Test Document 1",
        "informatieobjecttype": f"{CATALOGI_ROOT}informatieobjecttypen/c055908a-242b-469d-aead-8b838dc4ac7a",
        "vertrouwelijkheidaanduiding": "openbaar",
    }

    document_2 = {
        "url": f"{DOCUMENTEN_ROOT}enkelvoudiginformatieobjecten/9510addc-e396-442e-b76b-02705e45bb16",
        "titel": "Test Document 2",
        "informatieobjecttype": f"{CATALOGI_ROOT}informatieobjecttypen/10481de9-fdfd-4ce5-9d4b-10e844460d7d",
        "vertrouwelijkheidaanduiding": "geheim",
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
        "beginGeldigheid": "2020-12-01",
        "eindeGeldigheid": None,
        "concept": False,
    }

    iot_2 = {
        "url": document_2["informatieobjecttype"],
        "catalogus": f"{CATALOGI_ROOT}catalogussen/1b817d02-09dc-4e5f-9c98-cc9a991b81c6",
        "omschrijving": "Test Omschrijving 2",
        "vertrouwelijkheidaanduiding": "geheim",
        "beginGeldigheid": "2020-12-01",
        "eindeGeldigheid": None,
        "concept": False,
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
        PermissionDefinitionFactory.create(
            object_url="",
            permission=zaken_inzien.name,
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
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

    @skip("Adding one permissions to all iotypen is deprecated")
    def test_catalogus_but_no_informatieobjecttype(self, m):
        """Test that all the informatieobjecttypes within the catalogus are allowed"""
        self._set_up_mocks(m)

        user = UserFactory.create()
        self.app.set_user(user)

        with mock_zaak_detail_context(
            documents=make_document_objects(
                [self.document_1, self.document_2], [self.iot_1, self.iot_2]
            )
        ):
            response = self.app.get(self.zaak_detail_url, user=user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Test Document 1", response.html.text)
        self.assertIn("Test Document 2", response.html.text)

    @skip("Adding one permissions to all iotypen is deprecated")
    def test_catalogus_with_va_but_no_informatieobjecttype(self, m):
        """
        Test that all the informatieobjecttypes within the catalogus are allowed, but the
        document with VA higher than that given in the permission set is not shown.
        """
        self._set_up_mocks(m)

        user = UserFactory.create()
        self.app.set_user(user)

        # informatieobjecttype_catalogus in the permission, without informatieobjecttype_omschriving

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
        """Test that the user sees only the informatieobjecttype with allowed omschrijving"""
        self._set_up_mocks(m)

        user = UserFactory.create()
        self.app.set_user(user)

        PermissionDefinitionFactory.create(
            object_url="",
            permission=zaken_inzien.name,
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        PermissionDefinitionFactory.create(
            object_type=PermissionObjectType.document,
            object_url="",
            permission=zaken_download_documents.name,
            for_user=user,
            policy={
                "catalogus": self.iot_1["catalogus"],
                "iotype_omschrijving": "Test Omschrijving 1",
                "max_va": VertrouwelijkheidsAanduidingen.geheim,
            },
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


class ZaakProcessPermissionTests(ESMixin, ClearCachesMixin, TransactionWebTest):
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
            omschrijving="ZT1",
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
        PermissionDefinitionFactory.create(
            object_url="",
            permission=zaken_inzien.name,
            for_user=self.user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
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
        for permission_name in [
            zaken_inzien.name,
            zaakproces_usertasks.name,
            zaakproces_send_message.name,
        ]:
            PermissionDefinitionFactory.create(
                object_url="",
                permission=permission_name,
                for_user=self.user,
                policy={
                    "catalogus": self.zaaktype["catalogus"],
                    "zaaktype_omschrijving": "ZT1",
                    "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
                },
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
        for permission_name in [zaken_inzien.name, zaakproces_usertasks.name]:
            PermissionDefinitionFactory.create(
                object_url="",
                permission=permission_name,
                for_user=self.user,
                policy={
                    "catalogus": self.zaaktype["catalogus"],
                    "zaaktype_omschrijving": "ZT1",
                    "max_va": VertrouwelijkheidsAanduidingen.openbaar,
                },
            )
        url = reverse("core:claim-task")

        with patch("zac.camunda.user_tasks.api.extract_task_form", return_value=None):
            self.client.force_login(self.user)
            response = self.client.post(
                url,
                {"task_id": task["id"], "zaak": zaak["url"]},
            )
        self.assertEqual(response.status_code, 403)

    def test_claim_task_with_permission(self):
        task = get_camunda_task_mock()
        zaak_url = f"{ZAKEN_ROOT}zaken/5abd5f22-5317-4bf2-a750-7cf2f4910370"
        for permission_name in [zaken_inzien.name, zaakproces_usertasks.name]:
            PermissionDefinitionFactory.create(
                object_url="",
                permission=permission_name,
                for_user=self.user,
                policy={
                    "catalogus": self.zaaktype["catalogus"],
                    "zaaktype_omschrijving": "ZT1",
                    "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
                },
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
            "zac.camunda.user_tasks.api.extract_task_form",
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


@skip("OO restriction is deprecated")
@requests_mock.Mocker()
class OORestrictionTests(ESMixin, ClearCachesMixin, TransactionWebTest):
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
        kownsl = Service.objects.create(api_type=APITypes.orc, api_root=KOWNSL_ROOT)

        config = KownslConfig.get_solo()
        config.service = kownsl
        config.save()

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
            url=f"{ZAKEN_ROOT}zaken/1a32874b-5732-40b3-b8ae-9ecd90864a82",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=self.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )

    def test_oo_restriction_no_related_rol(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
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
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?for_zaak={self.zaak['url']}",
            json=[],
        )

        # gives them access to the page, zaaktype and VA specified -> visible
        oo = OrganisatieOnderdeelFactory.create(slug="oo-test")
        perm_set = PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )
        auth_profile = perm_set.authorizationprofile_set.get()
        auth_profile.oo = oo
        auth_profile.save()

        # mock out all the other calls - we're testing auth here
        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user, status=403)

        self.assertEqual(response.status_code, 403)

    def test_oo_restriction_with_related_rol(self, m):
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
        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            betrokkeneType="organisatorische_eenheid",
            betrokkeneIdentificatie={
                "identificatie": "oo-test",
            },
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([rol]),
        )

        # gives them access to the page, zaaktype and VA specified -> visible
        oo = OrganisatieOnderdeelFactory.create(slug="oo-test")
        perm_set = PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )
        auth_profile = perm_set.authorizationprofile_set.get()
        auth_profile.oo = oo
        auth_profile.save()

        # mock out all the other calls - we're testing auth here
        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

    def test_oo_restriction_with_unrelated_rollen(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
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
        rol1 = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            betrokkeneType="organisatorische_eenheid",
            betrokkeneIdentificatie={
                "identificatie": "oo-other",
            },
        )
        rol2 = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            betrokkeneType="medewerker",
            betrokkeneIdentificatie={
                "identificatie": "oo-test",
            },
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([rol1, rol2]),
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?for_zaak={self.zaak['url']}",
            json=[],
        )

        # gives them access to the page, zaaktype and VA specified -> visible
        oo = OrganisatieOnderdeelFactory.create(slug="oo-test")
        perm_set = PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )
        auth_profile = perm_set.authorizationprofile_set.get()
        auth_profile.oo = oo
        auth_profile.save()

        # mock out all the other calls - we're testing auth here
        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user, status=403)

        self.assertEqual(response.status_code, 403)

    def test_no_oo_set(self, m):
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
        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            betrokkeneType="organisatorische_eenheid",
            betrokkeneIdentificatie={
                "identificatie": "oo-test",
            },
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([rol]),
        )

        # gives them access to the page, zaaktype and VA specified -> visible
        OrganisatieOnderdeelFactory.create(slug="oo-test")
        perm_set = PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )
        auth_profile = perm_set.authorizationprofile_set.get()
        assert auth_profile.oo is None

        # mock out all the other calls - we're testing auth here
        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

    def test_access_as_superuser(self, m):
        user = SuperUserFactory.create()
        oo = OrganisatieOnderdeelFactory.create(slug="oo-test")
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
        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            betrokkeneType="organisatorische_eenheid",
            betrokkeneIdentificatie={
                "identificatie": "oo-test",
            },
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([rol]),
        )

        # set up other permissions that do not match the user to test superuser checks
        perm_set = PermissionSetFactory.create(
            permissions=[],
            for_user=user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )
        auth_profile = perm_set.authorizationprofile_set.get()
        auth_profile.oo = oo
        auth_profile.save()

        # mock out all the other calls - we're testing auth here
        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=user)

        self.assertEqual(response.status_code, 200)

    def test_multiple_oos_different_va(self, m):
        """
        Test that multiple auth profiles with different OOs don't give unintended access.

        See https://github.com/GemeenteUtrecht/zaakafhandelcomponent/pull/82#discussion_r501603971

            Should filtering also take into account zaak.va ? For example, let's imagine
            two auth profiles for user Bob:

            profile A with oo = "oo1" and 1 permission set for "zaaktype1" with va = "openbare"
            profile B with oo = "oo2" and 1 permission set for the same "zaaktype1" with va= "zeer_geheim"
            And now we are checking permissions for the zaak with zaaktype = zaaktype1 and va = "zeer_geheim"

            In current implementation both "oo1" and "oo2" would be selected here as relevant oos,
            but is it correct?
        """

        # set up the mocks
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
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
        rol1 = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            betrokkeneType="organisatorische_eenheid",
            betrokkeneIdentificatie={
                "identificatie": "oo1-test",
            },
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([rol1]),
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?for_zaak={self.zaak['url']}",
            json=[],
        )

        # set up the permissions
        oo1 = OrganisatieOnderdeelFactory.create(slug="oo1-test")
        oo2 = OrganisatieOnderdeelFactory.create(slug="oo2-test")

        # zaak is beperkt openbaar, and related to oo1-test. This AP gives no access,
        # even though the AP.oo matches, the VA does not.
        perm_set1 = PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.openbaar,
        )
        auth_profile = perm_set1.authorizationprofile_set.get()
        auth_profile.oo = oo1
        auth_profile.save()

        # zaak is beperkt openbaar, and related to oo1-test. This AP gives no access,
        # even though the VA matches, the AP.oo does not.
        perm_set2 = PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )
        auth_profile = perm_set2.authorizationprofile_set.get()
        auth_profile.oo = oo2
        auth_profile.save()

        # mock out all the other calls - we're testing auth here
        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user, status=403)

        self.assertEqual(response.status_code, 403)
