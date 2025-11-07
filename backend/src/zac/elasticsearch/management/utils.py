import os
from io import StringIO

from django.core.management.base import OutputWrapper

import psutil


def get_memory_usage():
    process = psutil.Process(os.getpid())
    mem_bytes = process.memory_info().rss  # in bytes
    mem_mbytes = mem_bytes / 1024**2
    return f"{mem_mbytes} MB"


class ProgressOutputWrapper(OutputWrapper):
    """Class to manage logs with and without progress bar"""

    def __init__(self, show_progress, *args, **kwargs):
        self.show_progress = show_progress

        super().__init__(*args, **kwargs)

    def write_without_progress(self, *args, **kwargs):
        """write in the stdout only if there is no progress bar"""
        if not self.show_progress:
            super().write(*args, **kwargs)

    def progress_file(self):
        return self if self.show_progress else StringIO()

    def start_progress(self):
        if self.show_progress:
            self.ending = ""

    def end_progress(self):
        if self.show_progress:
            self.ending = "\n"
