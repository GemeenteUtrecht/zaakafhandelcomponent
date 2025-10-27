from freezegun import freeze_time


class FreezeTimeMixin:
    """
    Safe mixin for Django 4.x test cases to freeze time per test instance.

    Usage:
        class MyTestCase(FreezeTimeMixin, TestCase):
            frozen_time = "2020-01-01T00:00:00Z"  # optional (defaults to now)

    Notes:
        - Works with Django 4+ (avoids deepcopy errors from class decorators)
        - Does NOT interfere with setUpTestData()
        - Freezer starts before setUp() and stops after tearDown()
    """

    frozen_time: str | None = None

    def setUp(self):
        # Start freezer before test code runs
        if self.frozen_time:
            self._freezer = freeze_time(self.frozen_time)
        else:
            self._freezer = freeze_time()  # defaults to now
        self._freezer.start()
        if hasattr(super(), "setUp"):
            super().setUp()

    def tearDown(self):
        # Stop freezer after test
        if hasattr(self, "_freezer"):
            self._freezer.stop()
        if hasattr(super(), "tearDown"):
            super().tearDown()
