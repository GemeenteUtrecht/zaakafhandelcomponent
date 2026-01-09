from os import path
from unittest.mock import patch

from django.conf import settings
from django.urls import reverse_lazy

import requests_mock
from elasticsearch_dsl import Index
from furl import furl
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import InformatieObjectType, ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.contrib.dowc.data import OpenDowc
from zac.contrib.dowc.models import DowcConfig
from zac.core.permissions import zaken_inzien, zaken_list_documents
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.api import (
    create_informatieobject_document,
    create_related_zaak_document,
    create_zaakinformatieobject_document,
)
from zac.elasticsearch.documents import InformatieObjectDocument
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak, ZaakInformatieObject

OBJECTS_ROOT = "http://objects.nl/api/v1/"
ZTC_ROOT = "http://catalogus.nl/api/v1/"
CATALOGUS_URL = f"{ZTC_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
ZRC_ROOT = "http://zaken.nl/api/v1/"
DRC_ROOT = "https://api.drc.nl/api/v1/"
DOWC_API_ROOT = "https://dowc.nl"


@requests_mock.Mocker()
class ESZaakDocumentsPermissionTests(ClearCachesMixin, APITransactionTestCase):
    catalogus = generate_oas_component(
        "ztc",
        "schemas/Catalogus",
        url=CATALOGUS_URL,
        domein="DOME",
    )
    zaaktype = generate_oas_component(
        "ztc",
        "schemas/ZaakType",
        url=f"{ZTC_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
        identificatie="ZT1",
        catalogus=CATALOGUS_URL,
        vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        omschrijving="ZT1",
    )
    zaak1 = generate_oas_component(
        "zrc",
        "schemas/Zaak",
        url=f"{ZRC_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
        zaaktype=zaaktype["url"],
        identificatie="zaak1",
        omschrijving="Some zaak 1",
        vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
    )
    zaak1_model = factory(Zaak, zaak1)
    zaak1_model.zaaktype = factory(ZaakType, zaaktype)

    endpoint = reverse_lazy(
        "zaak-documents-es",
        kwargs={
            "bronorganisatie": zaak1["bronorganisatie"],
            "identificatie": zaak1["identificatie"],
        },
    )
    patch_find_zaak = patch(
        "zac.core.api.views.find_zaak",
        return_value=zaak1_model,
    )

    def setUp(self):
        super().setUp()

        Service.objects.create(api_type=APITypes.zrc, api_root=ZRC_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=ZTC_ROOT)

        self.patch_find_zaak.start()
        self.addCleanup(self.patch_find_zaak.stop)

    def test_not_authenticated(self, m):
        response = self.client.post(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.post(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_perm_but_not_for_zaaktype(self, m):
        mock_service_oas_get(m, ZTC_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        zaaktype2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{ZTC_ROOT}zaaktypen/741c9d1e-de1c-46c6-9ae0-5696f7994ab6",
            identificatie="ZT2",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT2",
        )

        m.get(
            f"{ZTC_ROOT}zaaktypen",
            json=paginated_response([self.zaaktype, zaaktype2]),
        )
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name, zaken_list_documents.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": zaaktype2["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.post(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("zac.elasticsearch.drf_api.views.search_informatieobjects", return_value=[])
    @patch("zac.elasticsearch.drf_api.views.check_document_status", return_value=[])
    def test_is_superuser(self, m, *mocks):
        mock_service_oas_get(m, ZTC_ROOT, "ztc")
        mock_service_oas_get(m, ZRC_ROOT, "zrc")

        mock_resource_get(m, self.catalogus)
        m.get(f"{ZTC_ROOT}zaaktypen", json=paginated_response([self.zaaktype]))

        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.json()
        self.assertEqual(results["count"], 0)

    @patch("zac.elasticsearch.drf_api.views.search_informatieobjects", return_value=[])
    @patch("zac.elasticsearch.drf_api.views.check_document_status", return_value=[])
    def test_has_perms(self, m, *mocks):
        mock_service_oas_get(m, ZTC_ROOT, "ztc")
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        mock_resource_get(m, self.catalogus)
        m.get(f"{ZTC_ROOT}zaaktypen", json=paginated_response([self.zaaktype]))
        mock_resource_get(m, self.zaak1)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name, zaken_list_documents.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": self.zaaktype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.post(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.json()
        self.assertEqual(results["count"], 0)


@requests_mock.Mocker()
class ESZaakDocumentsResponseTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    catalogus = generate_oas_component(
        "ztc",
        "schemas/Catalogus",
        url=CATALOGUS_URL,
        domein="DOME",
    )
    zaaktype = generate_oas_component(
        "ztc",
        "schemas/ZaakType",
        url=f"{ZTC_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
        identificatie="ZT1",
        catalogus=CATALOGUS_URL,
        vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        omschrijving="ZT1",
    )
    zaak1 = generate_oas_component(
        "zrc",
        "schemas/Zaak",
        url=f"{ZRC_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
        zaaktype=zaaktype["url"],
        identificatie="zaak1",
        omschrijving="Some zaak 1",
        vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
    )
    zaak2 = generate_oas_component(
        "zrc",
        "schemas/Zaak",
        url=f"{ZRC_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca9",
        zaaktype=zaaktype["url"],
        bronorganisatie="002220647",
        identificatie="ZAAK2",
        vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
    )
    iot = factory(
        InformatieObjectType,
        generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{ZTC_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            omschrijving="bijlage",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            catalogus=catalogus["url"],
        ),
    )
    document1 = factory(
        Document,
        generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            informatieobjecttype=iot.url,
            url=f"{DRC_ROOT}enkelvoudiginformatieobjecten/8c21296c-af29-4f7a-86fd-02706a8187a0",
            titel="a",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            bestandsnaam="some-bestandsnaam1.ext1",
            locked=True,
        ),
    )
    document1.informatieobjecttype = iot
    document1.last_edited_date = None
    document2 = factory(
        Document,
        generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            informatieobjecttype=iot.url,
            url=f"{DRC_ROOT}enkelvoudiginformatieobjecten/8c21296c-af29-4f7a-86fd-02706a8187a1",
            titel="b",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            bestandsnaam="some-bestandsnaam2.ext2",
            locked=False,
        ),
    )
    document2.informatieobjecttype = iot
    document2.last_edited_date = None
    zio1 = factory(
        ZaakInformatieObject,
        generate_oas_component(
            "zrc",
            "schemas/ZaakInformatieObject",
            url=f"{ZRC_ROOT}zaakinformatieobjecten/8c21296c-af29-4f7a-86fd-02706a8187a2",
            zaak=zaak1["url"],
            informatieobject=document1.url,
            locked=False,
        ),
    )
    zio2 = factory(
        ZaakInformatieObject,
        generate_oas_component(
            "zrc",
            "schemas/ZaakInformatieObject",
            url=f"{ZRC_ROOT}zaakinformatieobjecten/8c21296c-af29-4f7a-86fd-02706a8187a3",
            zaak=zaak1["url"],
            informatieobject=document2.url,
        ),
    )
    zio3 = factory(
        ZaakInformatieObject,
        generate_oas_component(
            "zrc",
            "schemas/ZaakInformatieObject",
            url=f"{ZRC_ROOT}zaakinformatieobjecten/8c21296c-af29-4f7a-86fd-02706a8187a4",
            zaak=zaak2["url"],
            informatieobject=document1.url,
        ),
    )
    zaak1_model = factory(Zaak, zaak1)
    zaak1_model.zaaktype = factory(ZaakType, zaaktype)
    zaak2_model = factory(Zaak, zaak2)
    zaak2_model.zaaktype = factory(ZaakType, zaaktype)

    endpoint = reverse_lazy(
        "zaak-documents-es",
        kwargs={
            "bronorganisatie": zaak1["bronorganisatie"],
            "identificatie": zaak1["identificatie"],
        },
    )

    @staticmethod
    def clear_index(init=False):
        ESMixin.clear_index(init=init)
        Index(settings.ES_INDEX_DOCUMENTEN).delete(ignore=404)

        if init:
            InformatieObjectDocument.init()

    @staticmethod
    def refresh_index():
        ESMixin.refresh_index()
        Index(settings.ES_INDEX_DOCUMENTEN).refresh()

    def setUp(self):
        super().setUp()

        Service.objects.create(api_type=APITypes.zrc, api_root=ZRC_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=ZTC_ROOT)
        Service.objects.create(api_type=APITypes.drc, api_root=DRC_ROOT)
        self.dowc_service = Service.objects.create(
            label="dowc",
            api_type=APITypes.orc,
            api_root=DOWC_API_ROOT,
            auth_type=AuthTypes.zgw,
            header_key="Authorization",
            header_value="ApplicationToken some-token",
            client_id="zac",
            secret="supersecret",
            oas=f"{DOWC_API_ROOT}/api/v1",
            user_id="zac",
        )

        config = DowcConfig.get_solo()
        config.service = self.dowc_service
        config.save()

        fn, fext1 = path.splitext(self.document1.bestandsnaam)
        fn, fext2 = path.splitext(self.document2.bestandsnaam)
        patch_get_supported_extensions = patch(
            "zac.contrib.dowc.utils.get_supported_extensions",
            return_value=[fext1, fext2],
        )
        patch_get_supported_extensions.start()
        self.addCleanup(patch_get_supported_extensions.stop)

    def refresh_es(self, m):
        ESMixin.refresh_index()
        Index(settings.ES_INDEX_DOCUMENTEN).refresh()
        mock_service_oas_get(m, ZTC_ROOT, "ztc")
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        mock_service_oas_get(m, DOWC_API_ROOT, "dowc", oas_url=self.dowc_service.oas)

        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak1)
        m.get(
            f"{DOWC_API_ROOT}/api/v1/documenten?purpose=write",
            json=[
                {
                    "drcUrl": furl(self.document1.url)
                    .add({"versie": self.document1.versie})
                    .url,
                    "purpose": "write",
                    "magicUrl": "webdav-stuff:http://some-url.com/to-a-document/",
                    "uuid": str(self.document1.uuid),
                    "unversionedUrl": self.document1.url,
                }
            ],
        )

        zaak1_document = self.create_zaak_document(self.zaak1_model)
        zaak1_document.zaaktype = self.create_zaaktype_document(
            self.zaak1_model.zaaktype
        )
        zaak1_document.save()

        ziod1 = create_zaakinformatieobject_document(self.zio1)
        ziod1.save()
        ziod2 = create_zaakinformatieobject_document(self.zio2)
        ziod2.save()

        zaak2_document = self.create_zaak_document(self.zaak2_model)
        zaak2_document.zaaktype = self.create_zaaktype_document(
            self.zaak2_model.zaaktype
        )
        zaak2_document.save()

        ziod3 = create_zaakinformatieobject_document(self.zio3)
        ziod3.save()

        io1_document = create_informatieobject_document(self.document1)
        io1_document.related_zaken = [
            create_related_zaak_document(zaak)
            for zaak in [self.zaak1_model, self.zaak2_model]
        ]
        io1_document.save()

        io2_document = create_informatieobject_document(self.document2)
        io2_document.related_zaken = [create_related_zaak_document(self.zaak1_model)]
        io2_document.save()
        self.refresh_index()

    def test_response(self, m):
        self.refresh_es(m)
        mock_service_oas_get(m, ZRC_ROOT, "zrc")
        m.get(f"{ZTC_ROOT}zaaktypen", json=paginated_response([self.zaaktype]))
        mock_resource_get(m, self.zaak1)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name, zaken_list_documents.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": self.zaaktype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=user)

        with patch(
            "zac.elasticsearch.drf_api.views.check_document_status",
            return_value=[
                OpenDowc(
                    document=self.document1.url,
                    uuid="8a5885c3-9016-44c2-8ab9-0aceb9e5d8f8",
                    locked_by=user.email,
                )
            ],
        ):
            response = self.client.post(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.json()
        self.assertEqual(results["count"], 2)
        self.assertEqual(
            results["results"],
            [
                {
                    "auteur": self.document1.auteur,
                    "beschrijving": self.document1.beschrijving,
                    "bestandsnaam": self.document1.bestandsnaam,
                    "bestandsomvang": self.document1.bestandsomvang,
                    "bronorganisatie": self.document1.bronorganisatie,
                    "currentUserIsEditing": True,
                    "deleteUrl": f"/api/dowc/8a5885c3-9016-44c2-8ab9-0aceb9e5d8f8/",
                    "downloadUrl": reverse_lazy(
                        "core:download-document",
                        kwargs={
                            "bronorganisatie": self.document1.bronorganisatie,
                            "identificatie": self.document1.identificatie,
                        },
                    ),
                    "identificatie": self.document1.identificatie,
                    "informatieobjecttype": {
                        "url": self.iot.url,
                        "omschrijving": self.iot.omschrijving,
                    },
                    "lastEditedDate": None,
                    "locked": self.document1.locked,
                    "lockedBy": user.email if self.document1.locked else "",
                    "readUrl": f"/api/dowc/{self.document1.bronorganisatie}/{self.document1.identificatie}/read",
                    "relatedZaken": [],
                    "titel": self.document1.titel,
                    "url": self.document1.url,
                    "versie": self.document1.versie,
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.openbaar,
                    "writeUrl": f"/api/dowc/{self.document1.bronorganisatie}/{self.document1.identificatie}/write",
                },
                {
                    "auteur": self.document2.auteur,
                    "beschrijving": self.document2.beschrijving,
                    "bestandsnaam": self.document2.bestandsnaam,
                    "bestandsomvang": self.document2.bestandsomvang,
                    "bronorganisatie": self.document2.bronorganisatie,
                    "currentUserIsEditing": False,
                    "deleteUrl": "",
                    "downloadUrl": reverse_lazy(
                        "core:download-document",
                        kwargs={
                            "bronorganisatie": self.document2.bronorganisatie,
                            "identificatie": self.document2.identificatie,
                        },
                    ),
                    "identificatie": self.document2.identificatie,
                    "informatieobjecttype": {
                        "url": self.iot.url,
                        "omschrijving": self.iot.omschrijving,
                    },
                    "lastEditedDate": None,
                    "locked": self.document2.locked,
                    "lockedBy": "",
                    "readUrl": f"/api/dowc/{self.document2.bronorganisatie}/{self.document2.identificatie}/read",
                    "relatedZaken": [],
                    "titel": self.document2.titel,
                    "url": self.document2.url,
                    "versie": self.document2.versie,
                    "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.openbaar,
                    "writeUrl": f"/api/dowc/{self.document2.bronorganisatie}/{self.document2.identificatie}/write",
                },
            ],
        )
