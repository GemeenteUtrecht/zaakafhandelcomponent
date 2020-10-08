from django.core.management import BaseCommand

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search

from zac.accounts.models import User
from zac.accounts.permissions import UserPermissions
from zac.core.services import get_zaken

from ...documents import ZaakDocument


class Command(BaseCommand):
    help = "Create documents in ES by indexing all zaken from ZAKEN API"

    def handle(self, **options):
        self.index_zaken()

        self.stdout.write("Zaken have been indexed")

    def index_zaken(self):
        user, _ = User.objects.get_or_create(username="elastic", is_superuser=True)

        user_perms = UserPermissions(user)
        zaken = get_zaken(user_perms)

        # TODO replace with bulk API
        for zaak in zaken:
            zaak_document = ZaakDocument(
                meta={"id": zaak.uuid},
                url=zaak.url,
                zaaktype=zaak.zaaktype.url,
                vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding,
            )
            result = zaak_document.save()
