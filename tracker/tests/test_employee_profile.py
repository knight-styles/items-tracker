"""Tests for the Employee Equipment History Card (employee_profile view)."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from tracker.models import AppSettings, Employee, Item, UsageLog, User
from tracker.tests.base import BaseTestCase


class EmployeeProfileAccessTest(BaseTestCase):
    """Test basic access and permissions for the profile page."""

    def test_profile_loads_for_admin(self):
        self.login_admin()
        url = reverse("employee_profile", args=[self.emp1.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.emp1.name)

    def test_profile_loads_for_supervisor(self):
        self.login_supervisor()
        url = reverse("employee_profile", args=[self.emp1.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.emp1.name)

    def test_profile_requires_login(self):
        url = reverse("employee_profile", args=[self.emp1.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)

    def test_profile_404_for_invalid_employee(self):
        self.login_admin()
        url = reverse("employee_profile", args=[99999])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_profile_renders_for_inactive_employee(self):
        self.emp1.is_active = False
        self.emp1.save()
        self.login_admin()
        url = reverse("employee_profile", args=[self.emp1.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Inactive")


class EmployeeProfileKPITest(BaseTestCase):
    """Test KPI statistics accuracy."""

    def test_kpi_counts_match_database(self):
        now = timezone.now()
        # Create logs across time periods
        UsageLog.objects.create(employee=self.emp1, item=self.goggles, quantity=2, logged_by=self.supervisor)
        UsageLog.objects.create(employee=self.emp1, item=self.gloves, quantity=3, logged_by=self.supervisor)

        self.login_admin()
        url = reverse("employee_profile", args=[self.emp1.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        kpis = resp.context["kpis"]
        self.assertEqual(kpis["total_all_time"], 5)
        self.assertEqual(kpis["total_today"], 5)

    def test_kpi_zero_for_no_logs(self):
        self.login_admin()
        url = reverse("employee_profile", args=[self.emp2.pk])
        resp = self.client.get(url)
        kpis = resp.context["kpis"]
        self.assertEqual(kpis["total_all_time"], 0)
        self.assertEqual(kpis["total_today"], 0)
        self.assertEqual(kpis["total_week"], 0)
        self.assertEqual(kpis["total_month"], 0)


class EmployeeProfileEquipmentGridTest(BaseTestCase):
    """Test equipment grid cards content and status."""

    def test_equipment_cards_show_issued_items(self):
        UsageLog.objects.create(employee=self.emp1, item=self.goggles, quantity=1, logged_by=self.supervisor)
        UsageLog.objects.create(employee=self.emp1, item=self.gloves, quantity=1, logged_by=self.supervisor)

        self.login_admin()
        url = reverse("employee_profile", args=[self.emp1.pk])
        resp = self.client.get(url)
        cards = resp.context["equipment_cards"]
        self.assertEqual(len(cards), 2)
        item_names = {c["item"].name for c in cards}
        self.assertIn("Safety Goggles", item_names)
        self.assertIn("Work Gloves", item_names)

    def test_equipment_cards_today_status(self):
        UsageLog.objects.create(employee=self.emp1, item=self.goggles, quantity=1, logged_by=self.supervisor)

        self.login_admin()
        url = reverse("employee_profile", args=[self.emp1.pk])
        resp = self.client.get(url)
        cards = resp.context["equipment_cards"]
        self.assertEqual(cards[0]["status"], "today")

    def test_equipment_cards_empty_for_no_usage(self):
        self.login_admin()
        url = reverse("employee_profile", args=[self.emp2.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.context["equipment_count"], 0)
        self.assertContains(resp, "No equipment has been logged")


class EmployeeProfileHistoryTest(BaseTestCase):
    """Test the usage history table and date filters."""

    def test_history_lists_all_logs(self):
        UsageLog.objects.create(employee=self.emp1, item=self.goggles, quantity=1, logged_by=self.supervisor)
        UsageLog.objects.create(employee=self.emp1, item=self.gloves, quantity=2, logged_by=self.supervisor)

        self.login_admin()
        url = reverse("employee_profile", args=[self.emp1.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.context["result_count"], 2)

    def test_history_date_filter(self):
        UsageLog.objects.create(employee=self.emp1, item=self.goggles, quantity=1, logged_by=self.supervisor)

        self.login_admin()
        url = reverse("employee_profile", args=[self.emp1.pk])
        # Filter for today in application local timezone
        today_str = timezone.localdate().strftime("%Y-%m-%d")
        resp = self.client.get(url, {"date_from": today_str, "date_to": today_str})
        self.assertEqual(resp.context["result_count"], 1)

        # Filter for a past date range (should show 0)
        resp = self.client.get(url, {"date_from": "2020-01-01", "date_to": "2020-01-31"})
        self.assertEqual(resp.context["result_count"], 0)

    def test_history_pagination(self):
        for i in range(25):
            UsageLog.objects.create(employee=self.emp1, item=self.goggles, quantity=1, logged_by=self.supervisor)

        self.login_admin()
        url = reverse("employee_profile", args=[self.emp1.pk])
        resp = self.client.get(url)
        self.assertTrue(resp.context["page_obj"].paginator.num_pages > 1)

    def test_history_shows_logged_by_user(self):
        UsageLog.objects.create(employee=self.emp1, item=self.goggles, quantity=1, logged_by=self.supervisor)

        self.login_admin()
        url = reverse("employee_profile", args=[self.emp1.pk])
        resp = self.client.get(url)
        self.assertContains(resp, "super1")


class EmployeeProfileLinksTest(BaseTestCase):
    """Test that profile links appear on log and reports pages."""

    def test_reports_employee_summary_links_to_profile(self):
        self.login_admin()
        url = reverse("reports") + "?type=employee"
        resp = self.client.get(url)
        expected_url = reverse("employee_profile", args=[self.emp1.pk])
        self.assertContains(resp, expected_url)

    def test_reports_detail_has_profile_button(self):
        self.login_admin()
        url = reverse("reports_employee_detail", args=[self.emp1.pk])
        resp = self.client.get(url)
        expected_url = reverse("employee_profile", args=[self.emp1.pk])
        self.assertContains(resp, expected_url)
        self.assertContains(resp, "View Full Profile")
