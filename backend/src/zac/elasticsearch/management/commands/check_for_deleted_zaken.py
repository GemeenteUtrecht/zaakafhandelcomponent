import logging
from typing import Iterator

from django.conf import settings
from django.core.management import BaseCommand

from elasticsearch.helpers import bulk, scan
from elasticsearch_dsl.connections import connections

from zac.core.services import get_zaken_all

from ...utils import check_if_index_exists

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete documents from ES by checking if they exist in the ZAKEN API"

    def handle(self, **options):
        check_if_index_exists()
        self.zaken_uuids = [str(zaak.uuid) for zaak in get_zaken_all()]
        self.stdout.write("Found %d zaken in Open Zaak API." % len(self.zaken_uuids))
        self.bulk_delete_zaken()

    def find_deleted_zaken(self) -> Iterator[dict]:
        for zd in scan(
            connections.get_connection(),
            index=settings.ES_INDEX_ZAKEN,
            _source=False,
        ):
            if zd["_id"] not in self.zaken_uuids:
                logger.info("Zaak with uuid %s has been deleted.", zd["_id"])
                zd["_op_type"] = "delete"
                del zd["_type"]  # To shutup ElasticsearchDeprecation warnings
                yield zd

    def bulk_delete_zaken(self):
        bulk(connections.get_connection(), self.find_deleted_zaken())
