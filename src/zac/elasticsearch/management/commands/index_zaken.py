from django.conf import settings
from django.core.management import BaseCommand

from elasticsearch_dsl import Index

from zac.accounts.models import User
from zac.accounts.permissions import UserPermissions
from zac.core.services import get_rollen_all, get_zaken

from ...api import append_rol_to_document, create_zaak_document
from ...documents import ZaakDocument


class Command(BaseCommand):
    help = "Create documents in ES by indexing all zaken from ZAKEN API"

    def handle(self, **options):
        self.clear_zaken()
        self.index_zaken()
        self.index_rollen()

        self.stdout.write("Zaken have been indexed")

    def clear_zaken(self):
        zaken = Index(settings.ES_INDEX_ZAKEN)
        zaken.delete(ignore=404)

    def index_zaken(self):
        # create/refresh mapping in the ES
        ZaakDocument.init()

        user, _ = User.objects.get_or_create(username="elastic", is_superuser=True)
        user_perms = UserPermissions(user)

        zaken = get_zaken(user_perms, find_all=True)
        self.stdout.write(f"{len(zaken)} zaken are received from Zaken API")

        # TODO replace with bulk API
        for zaak in zaken:
            create_zaak_document(zaak)

    def index_rollen(self):
        rollen = get_rollen_all()
        self.stdout.write(f"{len(rollen)} rollen are received from Zaken API")

        for rol in rollen:
            append_rol_to_document(rol)
