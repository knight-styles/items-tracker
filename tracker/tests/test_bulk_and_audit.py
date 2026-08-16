from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from tracker.models import AuditLog, Employee, Item, User

from .base import BaseTestCase


def csv_file(name, content: bytes):
    return SimpleUploadedFile(name, content, content_type="text/csv")


class EmployeeBulkImportTests(BaseTestCase):
    def test_valid_rows_created(self):
        self.login_admin()
        f = csv_file("e.csv", b"name,code\nAnita Sharma,EMP-201\nVikram Singh,EMP-202\n")
        self.client.post(reverse("admin_employee_import"), {"csv_file": f})
        self.assertTrue(Employee.objects.filter(code="EMP-201").exists())
        self.assertTrue(Employee.objects.filter(code="EMP-202").exists())

    def test_duplicate_code_skipped_by_default(self):
        self.login_admin()
        f = csv_file("e.csv", f"name,code\nDuplicate,{self.emp1.code}\n".encode())
        self.client.post(reverse("admin_employee_import"), {"csv_file": f})
        self.assertEqual(Employee.objects.filter(code=self.emp1.code).count(), 1)
        self.emp1.refresh_from_db()
        self.assertEqual(self.emp1.name, "Ramesh Kumar")  # unchanged

    def test_duplicate_code_updated_when_flagged(self):
        self.login_admin()
        f = csv_file("e.csv", f"name,code\nRamesh Updated,{self.emp1.code}\n".encode())
        self.client.post(reverse("admin_employee_import"), {"csv_file": f, "update_existing": "on"})
        self.emp1.refresh_from_db()
        self.assertEqual(self.emp1.name, "Ramesh Updated")

    def test_missing_required_column_rejected(self):
        self.login_admin()
        f = csv_file("e.csv", b"full_name,employee_code\nX,Y\n")
        response = self.client.post(reverse("admin_employee_import"), {"csv_file": f}, follow=True)
        self.assertContains(response, "must have")

    def test_non_csv_extension_rejected(self):
        self.login_admin()
        f = SimpleUploadedFile("e.txt", b"name,code\nX,Y\n", content_type="text/plain")
        response = self.client.post(reverse("admin_employee_import"), {"csv_file": f}, follow=True)
        self.assertContains(response, "upload a .csv file")

    def test_supervisor_blocked(self):
        self.login_supervisor()
        f = csv_file("e.csv", b"name,code\nX,EMP-999\n")
        response = self.client.post(reverse("admin_employee_import"), {"csv_file": f}, follow=True)
        self.assertFalse(Employee.objects.filter(code="EMP-999").exists())


class ItemBulkImportTests(BaseTestCase):
    def test_valid_rows_created_with_stock(self):
        self.login_admin()
        f = csv_file("i.csv", b"name,current_stock\nFace Shield,25\n")
        self.client.post(reverse("admin_item_import"), {"csv_file": f})
        item = Item.objects.get(name="Face Shield")
        self.assertEqual(item.current_stock, 25)

    def test_invalid_stock_value_defaults_to_zero_with_warning(self):
        self.login_admin()
        f = csv_file("i.csv", b"name,current_stock\nRespirator,abc\n")
        response = self.client.post(reverse("admin_item_import"), {"csv_file": f}, follow=True)
        item = Item.objects.get(name="Respirator")
        self.assertEqual(item.current_stock, 0)
        self.assertContains(response, "invalid stock value")

    def test_update_existing_updates_stock(self):
        self.login_admin()
        f = csv_file("i.csv", f"name,current_stock\n{self.goggles.name},777\n".encode())
        self.client.post(reverse("admin_item_import"), {"csv_file": f, "update_existing": "on"})
        self.goggles.refresh_from_db()
        self.assertEqual(self.goggles.current_stock, 777)

    def test_duplicate_skipped_without_update_flag(self):
        self.login_admin()
        f = csv_file("i.csv", f"name,current_stock\n{self.goggles.name},777\n".encode())
        self.client.post(reverse("admin_item_import"), {"csv_file": f})  # no update_existing
        self.goggles.refresh_from_db()
        self.assertEqual(self.goggles.current_stock, 50)  # unchanged


class BulkDeactivateTests(BaseTestCase):
    def test_valid_codes_deactivated(self):
        self.login_admin()
        f = csv_file("d.csv", f"code\n{self.emp2.code}\n".encode())
        response = self.client.post(reverse("admin_employee_bulk_deactivate"), {"csv_file": f}, follow=True)
        self.emp2.refresh_from_db()
        self.assertFalse(self.emp2.is_active)

    def test_unknown_code_reported_not_found(self):
        self.login_admin()
        f = csv_file("d.csv", b"code\nEMP-DOES-NOT-EXIST\n")
        response = self.client.post(reverse("admin_employee_bulk_deactivate"), {"csv_file": f}, follow=True)
        self.assertContains(response, "EMP-DOES-NOT-EXIST")

    def test_deactivation_creates_audit_entry(self):
        self.login_admin()
        f = csv_file("d.csv", f"code\n{self.emp2.code}\n".encode())
        self.client.post(reverse("admin_employee_bulk_deactivate"), {"csv_file": f})
        self.assertTrue(
            AuditLog.objects.filter(action="bulk_deactivate", target_repr=self.emp2.name).exists()
        )

    def test_history_preserved_not_deleted(self):
        self.login_admin()
        f = csv_file("d.csv", f"code\n{self.emp2.code}\n".encode())
        self.client.post(reverse("admin_employee_bulk_deactivate"), {"csv_file": f})
        self.assertTrue(Employee.objects.filter(pk=self.emp2.pk).exists())


class AdminPasswordResetTests(BaseTestCase):
    def test_admin_can_reset_supervisor_password(self):
        self.login_admin()
        response = self.client.post(
            reverse("admin_user_reset_password", args=[self.supervisor.pk]),
            {"new_password1": "BrandNewPass456!", "new_password2": "BrandNewPass456!"},
        )
        self.assertRedirects(response, reverse("admin_users"))
        self.client.logout()
        logged_in = self.client.login(username="super1", password="BrandNewPass456!")
        self.assertTrue(logged_in)

    def test_password_reset_creates_audit_entry(self):
        self.login_admin()
        self.client.post(
            reverse("admin_user_reset_password", args=[self.supervisor.pk]),
            {"new_password1": "BrandNewPass456!", "new_password2": "BrandNewPass456!"},
        )
        self.assertTrue(
            AuditLog.objects.filter(action="password_reset", target_repr="super1").exists()
        )

    def test_mismatched_passwords_rejected(self):
        self.login_admin()
        response = self.client.post(
            reverse("admin_user_reset_password", args=[self.supervisor.pk]),
            {"new_password1": "One12345!", "new_password2": "Different12345!"},
        )
        self.assertEqual(response.status_code, 200)  # re-renders with errors
        self.client.logout()
        logged_in = self.client.login(username="super1", password="SuperPass123!")
        self.assertTrue(logged_in)  # original password still works

    def test_supervisor_blocked_from_resetting_passwords(self):
        self.login_supervisor()
        response = self.client.get(reverse("admin_user_reset_password", args=[self.supervisor.pk]), follow=True)
        self.assertRedirects(response, reverse("supervisor_log"))


class SettingsAuditTests(BaseTestCase):
    def test_settings_change_creates_audit_entry(self):
        self.login_admin()
        self.client.post(reverse("admin_settings"), {
            "period_days": 14, "reset_mode": "fixed_time", "reset_time": "20:00",
            "reset_hours": 20, "color_today": "#dc2626", "color_period": "#2563eb",
            "low_stock_threshold": 3, "bulk_issue_cooldown_days": 30,
        })
        self.assertTrue(AuditLog.objects.filter(action="settings_update").exists())

    def test_settings_unchanged_does_not_spam_audit_log(self):
        self.login_admin()
        # submit exactly the current values -- changed_data should be empty
        self.client.post(reverse("admin_settings"), {
            "period_days": self.settings.period_days,
            "reset_mode": self.settings.reset_mode,
            "reset_time": self.settings.reset_time.strftime("%H:%M"),
            "reset_hours": self.settings.reset_hours,
            "color_today": self.settings.color_today,
            "color_period": self.settings.color_period,
            "low_stock_threshold": self.settings.low_stock_threshold,
            "bulk_issue_cooldown_days": self.settings.bulk_issue_cooldown_days,
        })
        self.assertEqual(AuditLog.objects.filter(action="settings_update").count(), 0)
