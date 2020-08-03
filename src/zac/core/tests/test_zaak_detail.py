import contextlib
import datetime
from unittest.mock import patch

from django.conf import settings
from django.urls import reverse, reverse_lazy

import requests_mock
from django_webtest import TransactionWebTest
from freezegun import freeze_time
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import PermissionSetFactory, UserFactory
from zac.contrib.kownsl.data import Approval, ReviewRequest
from zac.tests.utils import (
    generate_oas_component,
    mock_service_oas_get,
    paginated_response,
)

from ..permissions import zaakproces_send_message, zaakproces_usertasks, zaken_inzien
from .mocks import get_camunda_task_mock
from .utils import ClearCachesMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"

BRONORGANISATIE = "123456782"
IDENTIFICATIE = "ZAAK-001"


@contextlib.contextmanager
def mock_zaak_detail_context():
    review_request_data = {
        "id": "45638aa6-e177-46cc-b580-43339795d5b5",
        "for_zaak": f"{ZAKEN_ROOT}zaak/123",
        "review_type": "approval",
        "frontend_url": f"https://kownsl.nl/45638aa6-e177-46cc-b580-43339795d5b5",
        "num_advices": 0,
        "num_approvals": 1,
        "num_assigned_users": 1,
    }
    approval_data = {
        "created": datetime.datetime(2020, 1, 1, 12, 00, 1),
        "author": {"username": "test_reviewer", "first_name": "", "last_name": "",},
        "approved": False,
    }
    review_request = factory(ReviewRequest, review_request_data)
    approval = factory(Approval, approval_data)

    m_get_statussen = patch("zac.core.views.zaken.get_statussen", return_value=[])
    m_get_statussen.start()
    m_get_documenten = patch(
        "zac.core.views.zaken.get_documenten", return_value=([], [])
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
        kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE,},
    )

    def setUp(self):
        super().setUp()

        self.user = UserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

    def test_login_required(self, m):
        response = self.app.get(self.url)

        self.assertRedirects(response, f"{settings.LOGIN_URL}?next={self.url}")

    def test_user_auth_no_perms(self, m):
        response = self.app.get(self.url, user=self.user, status=403)

        self.assertEqual(response.status_code, 403)

    def test_user_has_perm_but_not_for_zaaktype(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
        )
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            identificatie="ZT1",
        )
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={BRONORGANISATIE}&identificatie={IDENTIFICATIE}",
            json=paginated_response([zaak]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            json=zaaktype,
        )

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
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            url=f"{ZAKEN_ROOT}zaken/85a59d62-2ac7-432e-9ca7-4f6c9bde4d10",
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            catalogus=f"{CATALOGI_ROOT}catalogi/2fa14cce-12d0-4f57-8d5d-ecbdfbe06a5e",
            identificatie="ZT1",
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={zaaktype['catalogus']}",
            json=paginated_response([zaaktype]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={BRONORGANISATIE}&identificatie={IDENTIFICATIE}",
            json=paginated_response([zaak]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            json=zaaktype,
        )

        # gives them access to the page and zaaktype, but insufficient VA
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.openbaar,
        )

        response = self.app.get(self.url, user=self.user, status=403)

        self.assertEqual(response.status_code, 403)

    def test_user_has_perm(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/fa988e62-c1fe-4496-8c0f-29b85373e4df",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            catalogus=f"{CATALOGI_ROOT}catalogi/2fa14cce-12d0-4f57-8d5d-ecbdfbe06a5e",
            identificatie="ZT1",
        )
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={BRONORGANISATIE}&identificatie={IDENTIFICATIE}",
            json=paginated_response([zaak]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            json=zaaktype,
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={zaaktype['catalogus']}",
            json=paginated_response([zaaktype]),
        )

        # gives them access to the page, zaaktype and VA specified -> visible
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )

        # mock out all the other calls - we're testing auth here
        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

    def test_user_has_all_zaaktype_perms(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/fa988e62-c1fe-4496-8c0f-29b85373e4df",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            catalogus=f"{CATALOGI_ROOT}catalogi/2fa14cce-12d0-4f57-8d5d-ecbdfbe06a5e",
            identificatie="ZT1",
        )
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={BRONORGANISATIE}&identificatie={IDENTIFICATIE}",
            json=paginated_response([zaak]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            json=zaaktype,
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={zaaktype['catalogus']}",
            json=paginated_response([zaaktype]),
        )

        # gives them access to the page, catalogus and VA specified -> all zaaktypen visible
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=zaaktype["catalogus"],
            zaaktype_identificaties=[],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )

        # mock out all the other calls - we're testing auth here
        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

    @freeze_time("2020-01-02 12:00:01")
    def test_approval_case_details(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/fa988e62-c1fe-4496-8c0f-29b85373e4df",
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            catalogus=f"{CATALOGI_ROOT}catalogi/2fa14cce-12d0-4f57-8d5d-ecbdfbe06a5e",
            identificatie="ZT1",
        )
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={BRONORGANISATIE}&identificatie={IDENTIFICATIE}",
            json=paginated_response([zaak]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            json=zaaktype,
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={zaaktype['catalogus']}",
            json=paginated_response([zaaktype]),
        )

        # gives them access to the page, zaaktype and VA specified -> visible
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )
        with mock_zaak_detail_context():
            response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)


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
            f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={zaak['url']}", json=[],
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
            f"{ZAKEN_ROOT}statussen?zaak={zaak['url']}", json=paginated_response([]),
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
            f"https://camunda.example.com/engine-rest/task/{task['id']}", json=task,
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
            json={"value": zaak["url"], "type": "String",},
        )
        self.mocker.get(zaak["url"], json=zaak)
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name, zaakproces_usertasks.name,],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.openbaar,
        )
        url = reverse("core:claim-task")

        with patch("zac.core.camunda.extract_task_form", return_value=None):
            self.client.force_login(self.user)
            response = self.client.post(
                url, {"task_id": task["id"], "zaak": zaak["url"]},
            )
        self.assertEqual(response.status_code, 403)

    def test_claim_task_with_permission(self):
        task = get_camunda_task_mock()
        zaak_url = f"{ZAKEN_ROOT}zaken/5abd5f22-5317-4bf2-a750-7cf2f4910370"
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name, zaakproces_usertasks.name,],
            for_user=self.user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )

        url = reverse("core:claim-task")

        self.mocker.get(
            f"https://camunda.example.com/engine-rest/task/{task['id']}", json=task,
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
            json={"value": zaak_url, "type": "String",},
        )

        with patch("zac.core.views.processes.get_client") as m_client, patch(
            "zac.core.camunda.extract_task_form", return_value=None,
        ), patch(
            "zac.core.views.processes.get_roltypen", return_value=[],
        ):
            self.client.force_login(self.user)
            response = self.client.post(
                url, {"task_id": task["id"], "zaak": zaak_url, "next": "/"},
            )

        self.assertEqual(response.status_code, 302)
        m_client.return_value.post.assert_called_once()
