from django.test import TestCase

import requests_mock
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import RolOmschrijving, RolTypes
from zgw_consumers.constants import APITypes

from zac.contrib.brp.models import BRPConfig
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

from ..services import get_rollen
from .utils import ClearCachesMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"

BRP_API_ROOT = "https://api.brp.nl/api/v1/"
BSN1 = "1234567"
BSN2 = "890"


@requests_mock.Mocker()
class ZGWServiceTests(ClearCachesMixin, TestCase):
    zaaktype = generate_oas_component(
        "ztc",
        "schemas/ZaakType",
        url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
        catalogus=f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d",
    )
    roltype = generate_oas_component(
        "ztc",
        "schemas/RolType",
        url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
        zaaktype=zaaktype["url"],
        omschrijving_generiek=RolOmschrijving.initiator,
    )
    zaak1 = generate_oas_component(
        "zrc",
        "schemas/Zaak",
        url=f"{ZAKEN_ROOT}zaken/05b2c190-b1f6-4767-9e35-38bcf7702968",
        zaaktype=zaaktype["url"],
        identificatie="zaak1",
    )
    zaak2 = generate_oas_component(
        "zrc",
        "schemas/Zaak",
        url=f"{ZAKEN_ROOT}zaken/ee512886-d0d9-4c12-9bbb-78b0d22bfb61",
        zaaktype=zaaktype["url"],
        identificatie="zaak2",
    )

    @classmethod
    def setUpTestData(cls):
        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        brp_service = ServiceFactory.create(
            api_type=APITypes.orc, api_root=BRP_API_ROOT
        )

        config = BRPConfig.get_solo()
        config.service = brp_service
        config.save()

    def _setUpMocks(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, BRP_API_ROOT, "brp")

        rol1 = {
            "url": f"{ZAKEN_ROOT}rollen/ee512886-d0d9-4c12-9bbb-78b0d22bfb61",
            "zaak": self.zaak1["url"],
            "roltype": self.roltype["url"],
            "betrokkene": f"{BRP_API_ROOT}ingeschrevenpersonen/{BSN1}",
            "betrokkeneType": RolTypes.natuurlijk_persoon,
            "omschrijving": "some desc",
            "omschrijving_generiek": RolOmschrijving.initiator,
            "roltoelichting": "rol1",
            "registratiedatum": "2020-01-01",
            "indicatie_machtiging": "gemachtigde",
            "betrokkeneIdentificatie": None,
        }
        rol2 = {
            "url": f"{ZAKEN_ROOT}rollen/05b2c190-b1f6-4767-9e35-38bcf7702968",
            "zaak": self.zaak2["url"],
            "roltype": self.roltype["url"],
            "betrokkene": "",
            "betrokkeneType": RolTypes.natuurlijk_persoon,
            "omschrijving": "some desc",
            "omschrijving_generiek": RolOmschrijving.initiator,
            "roltoelichting": "rol1",
            "registratiedatum": "2020-01-01",
            "indicatie_machtiging": "gemachtigde",
            "betrokkeneIdentificatie": {
                "inpBsn": BSN2,
                "geslachtsnaam": "Vries",
                "voorvoegselGeslachtsnaam": "de",
                "voornamen": "Janneke",
            },
        }
        naturlijk_persoon = {
            "burgerservicenummer": BSN1,
            "geslachtsaanduiding": "man",
            "leeftijd": 34,
            "naam": {"geslachtsnaam": "Boer", "voornamen": "Jip", "voorvoegsel": "de"},
            "kiesrecht": {},
            "geboorte": {},
            "_links": {},
        }

        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak1['url']}",
            json=paginated_response([rol1]),
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak2['url']}",
            json=paginated_response([rol2]),
        )
        m.get(f"{BRP_API_ROOT}ingeschrevenpersonen/{BSN1}", json=naturlijk_persoon)

        self.zaak1 = factory(Zaak, self.zaak1)
        self.zaak2 = factory(Zaak, self.zaak2)

    def test_get_rollen_with_brp_request(self, m):
        self._setUpMocks(m)

        rollen = get_rollen(self.zaak1)

        self.assertEqual(len(rollen), 1)

        rol = rollen[0]
        self.assertEqual(rol.get_name(), "Jip de Boer")
        self.assertEqual(rol.get_identificatie(), BSN1)

    def test_get_rollen_no_brp_request(self, m):
        self._setUpMocks(m)

        rollen = get_rollen(self.zaak2)

        self.assertEqual(len(rollen), 1)

        rol = rollen[0]
        self.assertEqual(rol.get_name(), "Janneke de Vries")
        self.assertEqual(rol.get_identificatie(), BSN2)
