from abc import ABC, abstractmethod
from itertools import chain, islice
from typing import Iterator

from django.conf import settings
from django.core.management.base import CommandParser

from elasticsearch.helpers import bulk
from elasticsearch_dsl import Index
from elasticsearch_dsl.connections import connections

from zac.elasticsearch.documents import ZaakDocument

from ...utils import check_if_index_exists
from ..utils import ProgressOutputWrapper

NOTIMPLEMENTED_MSG = "Child classes must declare {field}."


class IndexCommand(ABC):
    help = "Create documents in ES by indexing all enkelvoudigeinformatieobjects from DRC API"
    _index = None
    _type = None
    _document = None
    _verbose_name = None
    _verbose_name_plural = None
    relies_on = dict()

    @property
    def index(self):
        if not self._index:
            raise NotImplementedError(NOTIMPLEMENTED_MSG.format(field="_index"))
        return self._index

    @property
    def type(self):
        if not self._type:
            raise NotImplementedError(NOTIMPLEMENTED_MSG.format(field="_type"))
        return self._type

    @property
    def document(self):
        if not self._document:
            raise NotImplementedError(NOTIMPLEMENTED_MSG.format(field="_document"))
        return self._document

    @property
    def verbose_name(self):
        """
        Defaults to _type.

        """
        if self._verbose_name:
            return self._verbose_name
        return self._type

    @property
    def verbose_name_plural(self):
        """
        Defaults to _type.

        """
        if self._verbose_name_plural:
            return self._verbose_name_plural
        return self._type

    def check_relies_on(self):
        for ind in self.relies_on.keys():
            check_if_index_exists(ind)

    def handle_reindex(self) -> list:
        # Edge case checks
        for doc in self.relies_on.values():
            if doc.search().extra(size=0).count() == 0:
                self.stdout.end_progress()
                return []

        # Fetch last <int:self.reindex_last> zaken, the ZIOs related to those zaken
        # and see if we have all the EIOs related to the ZIOs.
        return (
            ZaakDocument.search()
            .sort("-identificatie.keyword")
            .extra(size=self.reindex_last)
            .execute()
            .hits
        )

    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "--max-workers",
            type=int,
            help="Indicates the max number of parallel workers (for memory management). Defaults to 4.",
            default=4,
        )
        parser.add_argument(
            "--reindex-last",
            type=int,
            help="Indicates the number of the most recent documents to be reindexed.",
        )
        parser.add_argument(
            "--progress",
            "--show-progress",
            action="store_true",
            help=(
                "Show a progress bar. Showing a progress bar disables other "
                "fine-grained feedback."
            ),
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            help="Indicates the chunk size for number of a single ES scan iteration. Defaults to 100.",
            default=100,
        )

    def handle(self, **options):
        # redefine self.stdout as ProgressOutputWrapper cause logging is dependent whether
        # we have a progress bar
        show_progress = options["progress"]
        self.stdout = ProgressOutputWrapper(show_progress, out=self.stdout._out)
        self.max_workers = options["max_workers"]
        self.reindex_last = options["reindex_last"]
        self.chunk_size = options["chunk_size"]

        self.es_client = connections.get_connection()
        if self.reindex_last:
            self.handle_reindexing()
        else:
            self.handle_indexing()

    def get_chunks(self, iterable):
        iterator = iter(iterable)
        for first in iterator:
            yield chain([first], islice(iterator, self.chunk_size - 1))

    def handle_reindexing(self):
        # Make sure the index exists...
        check_if_index_exists(index=self.index)
        self.reindexed = (
            0  # To keep track of how many documents have already been reindexed.
        )
        self.bulk_upsert()
        self.stdout.write(
            f"{self.verbose_name_plural} for the last {self.reindex_last} ZAAKen are reindexed."
        )

    def handle_indexing(self):
        # If we're indexing everything - clear the index.
        self.clear_index()
        self.document.init()
        self.bulk_upsert()
        index = Index(self.index)
        index.refresh()
        count = index.search().extra(size=0).count()
        self.stdout.write(f"{count} {self.verbose_name_plural} are received.")

    def bulk_upsert(self):
        bulk(
            self.es_client,
            self.batch_index(),
            max_retries=settings.ES_MAX_RETRIES,
            max_backoff=settings.ES_MAX_BACKOFF,
            chunk_size=settings.ES_CHUNK_SIZE,
        )

    def check_if_done_batching(self) -> bool:
        if self.reindex_last and self.reindex_last - self.reindexed == 0:
            return True
        return False

    def clear_index(self):
        index = Index(self.index)
        index.delete(ignore=404)

    @abstractmethod
    def batch_index(self) -> Iterator:
        self.check_relies_on()
        pass
