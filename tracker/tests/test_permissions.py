from django.urls import reverse

from .base import BaseTestCase

ADMIN_ONLY_URLS = [
    "admin_employees", "admin_items", "admin_users", "admin_settings", "admin_audit_log",
]


class AdminOnlyPageTests(BaseTestCase):
    def test_admin_can_access_admin_only_pages(self):
        self.login_admin()
        for name in ADMIN_ONLY_URLS:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)

    def test_supervisor_blocked_from_admin_only_pages(self):
        self.login_supervisor()
        for name in ADMIN_ONLY_URLS:
            with self.subTest(url=name):
                response = self.client.get(reverse(name), follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertRedirects(response, reverse("supervisor_log"))

    def test_supervisor_blocked_from_item_creation_directly(self):
        self.login_supervisor()
        response = self.client.post(
            reverse("admin_item_add"), {"name": "Hack Item", "current_stock": 999}, follow=True
        )
        from tracker.models import Item
        self.assertFalse(Item.objects.filter(name="Hack Item").exists())


class SupervisorPageAccessTests(BaseTestCase):
    """Supervisor-only pages are also reachable by Admin (superset access)."""

    def test_supervisor_can_access_own_pages(self):
        self.login_supervisor()
        for name in ["supervisor_log", "supervisor_add_employee", "supervisor_stock", "reports"]:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)

    def test_admin_can_also_access_supervisor_pages(self):
        self.login_admin()
        for name in ["supervisor_log", "supervisor_add_employee", "supervisor_stock"]:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)

    def test_supervisor_add_employee_has_no_delete_button(self):
        self.login_supervisor()
        response = self.client.get(reverse("supervisor_add_employee"))
        self.assertNotContains(response, "Delete")
        self.assertNotContains(response, "Deactivate")

    def test_supervisor_cannot_delete_employee_via_admin_url(self):
        self.login_supervisor()
        response = self.client.post(
            reverse("admin_employee_delete", args=[self.emp1.pk]), follow=True
        )
        self.emp1.refresh_from_db()
        self.assertTrue(self.emp1.pk)  # still exists
        self.assertRedirects(response, reverse("supervisor_log"))


class SharedPageTests(BaseTestCase):
    def test_reports_accessible_by_both_roles(self):
        for login in (self.login_admin, self.login_supervisor):
            login()
            response = self.client.get(reverse("reports"))
            self.assertEqual(response.status_code, 200)
            self.client.logout()

    def test_unauthenticated_blocked_everywhere(self):
        for name in ["admin_dashboard", "supervisor_log", "reports", "admin_employees"]:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
