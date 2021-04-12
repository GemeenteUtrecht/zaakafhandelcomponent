from django.conf import settings
from django.core.management import BaseCommand

from elasticsearch_dsl import Index
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.concurrent import parallel

from zac.core.services import fetch_zaaktype, get_rollen_all, get_zaken_all

from ...api import (
    append_rol_to_document,
    append_zaaktype_to_document,
    create_zaak_document,
    update_eigenschappen_in_zaak_document,
)
from ...documents import ZaakDocument


class Command(BaseCommand):
    help = "Create documents in ES by indexing all zaken from ZAKEN API"

    def handle(self, **options):
        self.clear_zaken_index()

        zaken = get_zaken_all()
        self.stdout.write(f"{len(zaken)} zaken are received from Zaken API")

        self.index_zaken(zaken)
        self.index_rollen()
        self.index_zaak_eigenschappen(zaken)

        self.stdout.write("Zaken have been indexed")

    def clear_zaken_index(self):
        zaken = Index(settings.ES_INDEX_ZAKEN)
        zaken.delete(ignore=404)

    def index_zaken(self, zaken):
        # create/refresh mapping in the ES
        ZaakDocument.init()

        zaaktype_urls = {
            zaak.zaaktype.url if isinstance(zaak.zaaktype, ZaakType) else zaak.zaaktype
            for zaak in zaken
        }
        with parallel() as executor:
            results = executor.map(fetch_zaaktype, list(zaaktype_urls))

        zaaktypen = {zaaktype.url: zaaktype for zaaktype in list(results)}

        # TODO replace with bulk API
        for zaak in zaken:
            zaaktype_url = (
                zaak.zaaktype
                if not isinstance(zaak.zaaktype, ZaakType)
                else zaak.zaaktype.url
            )
            zaak.zaaktype = zaaktypen[zaaktype_url]
            create_zaak_document(zaak)

    def index_rollen(self):
        rollen = get_rollen_all()
        self.stdout.write(f"{len(rollen)} rollen are received from Zaken API")

        for rol in rollen:
            append_rol_to_document(rol)

    def index_zaak_eigenschappen(self, zaken):
        for zaak in zaken:
            if zaak.eigenschappen:
                update_eigenschappen_in_zaak_document(zaak)

        self.stdout.write(
            "eigenschappen were indexed for {} zaken".format(
                len([zaak for zaak in zaken if zaak.eigenschappen])
            )
        )
