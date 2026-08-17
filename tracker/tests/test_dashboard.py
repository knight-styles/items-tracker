"""Tests for the Admin Analytics Dashboard."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from tracker.models import AppSettings, Employee, Item, UsageLog
from tracker.tests.base import BaseTestCase


class DashboardAccessTests(BaseTestCase):
    """Verify access control on Admin Dashboard."""

    def test_dashboard_accessible_to_admin(self):
        self.login_admin()
        resp = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Executive Dashboard")

    def test_dashboard_forbidden_to_supervisor(self):
        self.login_supervisor()
        resp = self.client.get(reverse("admin_dashboard"), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertRedirects(resp, reverse("supervisor_log"))

    def test_dashboard_redirects_unauthenticated(self):
        resp = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)


class DashboardMetricsTests(BaseTestCase):
    """Verify analytics and calculations on the dashboard."""

    def test_dashboard_renders_with_empty_database(self):
        UsageLog.objects.all().delete()
        Employee.objects.all().delete()
        Item.objects.all().delete()

        self.login_admin()
        resp = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total_employees"], 0)
        self.assertEqual(resp.context["total_items"], 0)
        self.assertEqual(resp.context["total_stock_qty"], 0)
        self.assertEqual(resp.context["compliance_rate"], 0)
        self.assertEqual(resp.context["variance_rate"], 0.0)
        self.assertEqual(resp.context["integrity_score"], 100.0)

    def test_dashboard_renders_with_usage_and_anomalies(self):
        self.login_admin()
        now = timezone.now()

        # Create usage logs
        UsageLog.objects.create(employee=self.emp1, item=self.goggles, quantity=2, logged_by=self.supervisor)
        UsageLog.objects.create(employee=self.emp1, item=self.gloves, quantity=1, logged_by=self.supervisor)
        UsageLog.objects.create(employee=self.emp1, item=self.goggles, quantity=1, logged_by=self.supervisor)
        UsageLog.objects.create(employee=self.emp2, item=self.earplugs, quantity=5, logged_by=self.supervisor)

        resp = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(resp.context["total_issued_30d"], 9)
        self.assertGreater(resp.context["compliance_rate"], 0)
        self.assertTrue(len(resp.context["monthly_trend"]) == 4)
        self.assertTrue(len(resp.context["trend"]) == 7)
        self.assertTrue(resp.context["integrity_score"] >= 0.0)
