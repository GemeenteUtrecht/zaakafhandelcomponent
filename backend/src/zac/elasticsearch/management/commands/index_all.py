from django.core.management import BaseCommand, call_command
from django.core.management.base import CommandParser

from ..utils import ProgressOutputWrapper


class Command(BaseCommand):
    help = "Indexes ZAAKs, ZAAKINFORMATIEOBJECTen, ZAAKOBJECTen, INFORMATIEOBJECTen and OBJECTen."

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
            help="Indicates the chunk size for number of ZIOs in a single iteration. Defaults to 100.",
            default=100,
        )

    def handle(self, **options):
        # redefine self.stdout as ProgressOutputWrapper cause logging is dependent whether
        # we have a progress bar
        show_progress = options["progress"]
        self.stdout = ProgressOutputWrapper(show_progress, out=self.stdout._out)

        args = []
        if reindex_last := options.get("reindex_last"):
            args.append(f"--reindex-last={reindex_last}")

        if (progress := options.get("progress")) or (
            progress := options.get("show_progress")
        ):
            args.append(f"--progress={progress}")

        if max_workers := options.get("max_workers"):
            args.append(f"--max-workers={max_workers}")

        if chunk_size := options.get("chunk_size"):
            args.append(f"--chunk-size={chunk_size}")

        index_these = [
            "index_zaken",
            "index_zaakinformatieobjecten",
            "index_zaakobjecten",
            "index_documenten_verzaking",
            "index_objecten",
        ]

        for index_this in index_these:
            self.stdout.write(f"Calling {index_this} {' '.join(args)}.")
            call_command(index_this, *args)
            self.stdout.write(f"Done with {index_this}.")
