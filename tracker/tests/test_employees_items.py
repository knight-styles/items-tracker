from django.urls import reverse

from tracker.models import AuditLog, Employee, Item, UsageLog

from .base import BaseTestCase


class EmployeeCRUDTests(BaseTestCase):
    def test_admin_can_add_employee(self):
        self.login_admin()
        response = self.client.post(
            reverse("admin_employee_add"), {"name": "New Guy", "code": "EMP-900", "is_active": "on"}
        )
        self.assertRedirects(response, reverse("admin_employees"))
        self.assertTrue(Employee.objects.filter(code="EMP-900").exists())

    def test_duplicate_code_rejected(self):
        self.login_admin()
        response = self.client.post(
            reverse("admin_employee_add"), {"name": "Dup", "code": self.emp1.code, "is_active": "on"}
        )
        self.assertEqual(response.status_code, 200)  # re-renders form, no redirect
        self.assertEqual(Employee.objects.filter(code=self.emp1.code).count(), 1)

    def test_admin_can_deactivate_and_reactivate(self):
        self.login_admin()
        self.client.post(reverse("admin_employee_toggle_active", args=[self.emp1.pk]))
        self.emp1.refresh_from_db()
        self.assertFalse(self.emp1.is_active)
        self.client.post(reverse("admin_employee_toggle_active", args=[self.emp1.pk]))
        self.emp1.refresh_from_db()
        self.assertTrue(self.emp1.is_active)

    def test_delete_blocked_when_usage_history_exists(self):
        UsageLog.objects.create(employee=self.emp1, item=self.goggles, logged_by=self.supervisor)
        self.login_admin()
        response = self.client.post(reverse("admin_employee_delete", args=[self.emp1.pk]), follow=True)
        self.assertContains(response, "usage history exists")
        self.assertTrue(Employee.objects.filter(pk=self.emp1.pk).exists())

    def test_delete_succeeds_with_no_history(self):
        self.login_admin()
        response = self.client.post(reverse("admin_employee_delete", args=[self.emp2.pk]), follow=True)
        self.assertFalse(Employee.objects.filter(pk=self.emp2.pk).exists())

    def test_supervisor_can_add_and_edit_but_not_deactivate(self):
        self.login_supervisor()
        response = self.client.post(
            reverse("supervisor_employee_add"), {"name": "Sup Added", "code": "EMP-901"}
        )
        self.assertRedirects(response, reverse("supervisor_add_employee"))
        emp = Employee.objects.get(code="EMP-901")
        self.assertTrue(emp.is_active)  # forced active on create

        response = self.client.post(
            reverse("supervisor_employee_edit", args=[emp.pk]), {"name": "Sup Edited", "code": "EMP-901"}
        )
        emp.refresh_from_db()
        self.assertEqual(emp.name, "Sup Edited")

    def test_toggle_active_creates_audit_entry(self):
        self.login_admin()
        self.client.post(reverse("admin_employee_toggle_active", args=[self.emp1.pk]))
        self.assertTrue(
            AuditLog.objects.filter(action="deactivate", target_type="Employee", target_repr=self.emp1.name).exists()
        )


class ItemCRUDTests(BaseTestCase):
    def test_admin_can_add_item(self):
        self.login_admin()
        response = self.client.post(
            reverse("admin_item_add"), {"name": "Face Shield", "current_stock": 20, "is_active": "on"}
        )
        self.assertRedirects(response, reverse("admin_items"))
        self.assertTrue(Item.objects.filter(name="Face Shield").exists())

    def test_duplicate_name_rejected(self):
        self.login_admin()
        response = self.client.post(
            reverse("admin_item_add"), {"name": self.goggles.name, "current_stock": 5, "is_active": "on"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Item.objects.filter(name=self.goggles.name).count(), 1)

    def test_delete_blocked_when_usage_history_exists(self):
        UsageLog.objects.create(employee=self.emp1, item=self.goggles, logged_by=self.supervisor)
        self.login_admin()
        response = self.client.post(reverse("admin_item_delete", args=[self.goggles.pk]), follow=True)
        self.assertContains(response, "usage history exists")
        self.assertTrue(Item.objects.filter(pk=self.goggles.pk).exists())

    def test_low_stock_highlight_uses_settings_threshold(self):
        self.settings.low_stock_threshold = 100
        self.settings.save()
        self.login_admin()
        response = self.client.get(reverse("admin_items"))
        self.assertContains(response, "Low Stock")  # goggles(50), gloves(30) both below 100

    def test_admin_can_add_item_with_image(self):
        import io
        from PIL import Image as PILImage
        from django.core.files.uploadedfile import SimpleUploadedFile

        file_obj = io.BytesIO()
        img = PILImage.new("RGB", (50, 50), color="blue")
        img.save(file_obj, format="JPEG")
        file_obj.seek(0)
        uploaded_image = SimpleUploadedFile("shield.jpg", file_obj.read(), content_type="image/jpeg")

        self.login_admin()
        response = self.client.post(
            reverse("admin_item_add"),
            {
                "name": "Welding Shield",
                "current_stock": 15,
                "image": uploaded_image,
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("admin_items"))
        item = Item.objects.filter(name="Welding Shield").first()
        self.assertIsNotNone(item)
        self.assertTrue(bool(item.image))
        self.assertTrue(item.image.name.startswith("item_images/"))
        self.assertIn("/media/item_images/", item.get_image_url())

    def test_admin_can_edit_item_image(self):
        import io
        from PIL import Image as PILImage
        from django.core.files.uploadedfile import SimpleUploadedFile

        file_obj = io.BytesIO()
        img = PILImage.new("RGB", (50, 50), color="green")
        img.save(file_obj, format="JPEG")
        file_obj.seek(0)
        uploaded_image = SimpleUploadedFile("new_goggles.jpg", file_obj.read(), content_type="image/jpeg")

        self.login_admin()
        response = self.client.post(
            reverse("admin_item_edit", args=[self.goggles.pk]),
            {
                "name": self.goggles.name,
                "current_stock": self.goggles.current_stock,
                "image": uploaded_image,
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("admin_items"))
        self.goggles.refresh_from_db()
        self.assertTrue(bool(self.goggles.image))
        self.assertIn("/media/item_images/", self.goggles.get_image_url())

