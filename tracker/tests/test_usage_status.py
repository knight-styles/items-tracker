from datetime import time, timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from tracker.models import AppSettings
from tracker.usage_status import compute_item_status


class ComputeItemStatusTests(SimpleTestCase):
    def setUp(self):
        self.settings = AppSettings(period_days=7, reset_mode=AppSettings.ResetMode.FIXED_TIME, reset_time=time(0, 0))
        # Pin to a fixed mid-day reference so midnight-boundary tests are
        # never flaky near midnight (e.g. "now - 1h" crossing to previous day).
        local_now = timezone.localtime(timezone.now())
        self.now = local_now.replace(hour=10, minute=0, second=0, microsecond=0)

    def test_never_logged_is_normal(self):
        self.assertEqual(compute_item_status(None, self.settings, now=self.now), "normal")

    def test_fixed_time_midnight_reset_logged_today(self):
        self.assertEqual(
            compute_item_status(self.now - timedelta(hours=1), self.settings, now=self.now), "today"
        )

    def test_fixed_time_midnight_reset_logged_yesterday_is_period(self):
        self.assertEqual(
            compute_item_status(self.now - timedelta(hours=25), self.settings, now=self.now), "period"
        )

    def test_outside_period_is_normal(self):
        self.assertEqual(
            compute_item_status(self.now - timedelta(days=10), self.settings, now=self.now), "normal"
        )

    def test_hours_after_mode_within_window_is_today(self):
        self.settings.reset_mode = AppSettings.ResetMode.HOURS_AFTER
        self.settings.reset_hours = 20
        self.assertEqual(
            compute_item_status(self.now - timedelta(hours=5), self.settings, now=self.now), "today"
        )

    def test_hours_after_mode_past_window_is_period(self):
        self.settings.reset_mode = AppSettings.ResetMode.HOURS_AFTER
        self.settings.reset_hours = 20
        self.assertEqual(
            compute_item_status(self.now - timedelta(hours=25), self.settings, now=self.now), "period"
        )

    def test_non_midnight_reset_boundary_before_reset_is_period(self):
        """A log at 19:30 with a 20:00 reset counted as 'today' -- checked at 21:00 same day."""
        self.settings.reset_time = time(20, 0)
        local_now = timezone.localtime(self.now)
        reference_now = local_now.replace(hour=21, minute=0, second=0, microsecond=0)
        log_time = local_now.replace(hour=19, minute=30, second=0, microsecond=0)
        self.assertEqual(compute_item_status(log_time, self.settings, now=reference_now), "period")

    def test_non_midnight_reset_boundary_after_reset_is_today(self):
        self.settings.reset_time = time(20, 0)
        local_now = timezone.localtime(self.now)
        reference_now = local_now.replace(hour=21, minute=0, second=0, microsecond=0)
        log_time = local_now.replace(hour=20, minute=30, second=0, microsecond=0)
        self.assertEqual(compute_item_status(log_time, self.settings, now=reference_now), "today")
