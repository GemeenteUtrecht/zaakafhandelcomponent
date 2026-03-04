"""
Management command to fix va_order values in Elasticsearch indices.

Recalculates va_order from the vertrouwelijkheidaanduiding string field
using Elasticsearch's update_by_query API with a Painless script.
No data is fetched from Open Zaak - this only updates ES in-place.

For nested related_zaken documents (which don't store the VA string),
the old integer values are mapped to new ones directly.
"""
import logging

from django.conf import settings
from django.core.management import BaseCommand

from elasticsearch import Elasticsearch

from zac.accounts.datastructures import VA_ORDER

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Fix va_order values in ES indices by recalculating them "
        "from the vertrouwelijkheidaanduiding string field. "
        "Uses update_by_query so no full reindex is needed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only show what would be updated without making changes.",
        )

    def get_es_client(self):
        return Elasticsearch(settings.ELASTICSEARCH_DSL["default"]["hosts"])

    def handle(self, **options):
        dry_run = options["dry_run"]
        es = self.get_es_client()

        if dry_run:
            self.stdout.write("DRY RUN - no changes will be made\n")

        self.stdout.write("VA_ORDER mapping: %s\n\n" % VA_ORDER)

        # Fix the main zaken index
        self.fix_zaken_index(es, dry_run)

        # Fix nested related_zaken in objecten index
        self.fix_nested_va_order(es, settings.ES_INDEX_OBJECTEN, dry_run)

        # Fix nested related_zaken in documenten index
        self.fix_nested_va_order(es, settings.ES_INDEX_DOCUMENTEN, dry_run)

        self.stdout.write("\nDone.\n")

    def _build_va_painless_map(self):
        """Build Painless HashMap initialization for VA_ORDER."""
        parts = []
        for va_string, va_int in VA_ORDER.items():
            parts.append("m.put('%s', %d)" % (va_string, va_int))
        return "def m = new HashMap(); " + "; ".join(parts) + "; "

    def fix_zaken_index(self, es, dry_run):
        index = settings.ES_INDEX_ZAKEN
        self.stdout.write("=== Fixing %s index ===\n" % index)

        painless_map = self._build_va_painless_map()
        script = (
            painless_map
            + "if (ctx._source.vertrouwelijkheidaanduiding != null "
            + "&& m.containsKey(ctx._source.vertrouwelijkheidaanduiding)) { "
            + "ctx._source.va_order = m.get(ctx._source.vertrouwelijkheidaanduiding); "
            + "} else { ctx.op = 'noop'; }"
        )

        if dry_run:
            count = es.count(index=index)["count"]
            self.stdout.write("  Total documents: %d\n" % count)

            sample = es.search(
                index=index,
                body={
                    "size": 5,
                    "_source": ["vertrouwelijkheidaanduiding", "va_order"],
                },
            )
            for hit in sample["hits"]["hits"]:
                src = hit["_source"]
                va = src.get("vertrouwelijkheidaanduiding")
                old = src.get("va_order")
                new = VA_ORDER.get(va, "?")
                self.stdout.write(
                    "  Sample: va=%s, old va_order=%s, new va_order=%s\n"
                    % (va, old, new)
                )
            return

        result = es.update_by_query(
            index=index,
            body={
                "script": {
                    "source": script,
                    "lang": "painless",
                },
                "query": {"match_all": {}},
            },
            conflicts="proceed",
            request_timeout=600,
        )
        updated = result.get("updated", 0)
        noops = result.get("noops", 0)
        failures = result.get("failures", [])
        self.stdout.write(
            "  Updated: %d, Noops: %d, Failures: %d\n"
            % (updated, noops, len(failures))
        )
        if failures:
            for f in failures[:5]:
                self.stdout.write("  Failure: %s\n" % f)

    def fix_nested_va_order(self, es, index, dry_run):
        self.stdout.write(
            "\n=== Fixing nested related_zaken.va_order in %s ===\n" % index
        )

        if not es.indices.exists(index=index):
            self.stdout.write("  Index %s does not exist, skipping\n" % index)
            return

        # RelatedZaakDocument does NOT have vertrouwelijkheidaanduiding string,
        # only va_order integer. We need to map old values to new values.
        # Old mapping: index * 10 (0, 10, 20, 30, 40, 50, 60, 70)
        # New mapping: index (0, 1, 2, 3, 4, 5, 6, 7)
        # So we divide by 10: new_va_order = old_va_order / 10
        script = (
            "if (ctx._source.related_zaken != null) { "
            "for (rz in ctx._source.related_zaken) { "
            "if (rz.va_order != null && rz.va_order > 7) { "
            "rz.va_order = rz.va_order / 10; "
            "} } }"
        )

        if dry_run:
            count = es.count(index=index)["count"]
            self.stdout.write("  Total documents: %d\n" % count)

            # Sample a document with related_zaken
            sample = es.search(
                index=index,
                body={
                    "size": 3,
                    "_source": ["related_zaken.va_order"],
                    "query": {
                        "nested": {
                            "path": "related_zaken",
                            "query": {
                                "exists": {"field": "related_zaken.va_order"}
                            },
                        }
                    },
                },
            )
            for hit in sample["hits"]["hits"]:
                rz_list = hit["_source"].get("related_zaken", [])
                for rz in rz_list[:3]:
                    old = rz.get("va_order")
                    new = old // 10 if old is not None and old > 7 else old
                    self.stdout.write(
                        "  Sample nested: old va_order=%s, new va_order=%s\n"
                        % (old, new)
                    )
            return

        result = es.update_by_query(
            index=index,
            body={
                "script": {
                    "source": script,
                    "lang": "painless",
                },
                "query": {
                    "nested": {
                        "path": "related_zaken",
                        "query": {
                            "exists": {"field": "related_zaken.va_order"}
                        },
                    }
                },
            },
            conflicts="proceed",
            request_timeout=600,
        )
        updated = result.get("updated", 0)
        noops = result.get("noops", 0)
        failures = result.get("failures", [])
        self.stdout.write(
            "  Updated: %d, Noops: %d, Failures: %d\n"
            % (updated, noops, len(failures))
        )
        if failures:
            for f in failures[:5]:
                self.stdout.write("  Failure: %s\n" % f)
