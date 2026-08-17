from django.urls import reverse

from tracker.models import Employee, Item, UsageLog

from .base import BaseTestCase


class LogSubmissionTests(BaseTestCase):
    def test_valid_submission_creates_logs_and_decrements_stock(self):
        self.login_supervisor()
        response = self.client.post(
            reverse("supervisor_log_submit"),
            {"employee_id": self.emp1.pk, "item": [self.goggles.pk, self.gloves.pk]},
        )
        self.assertEqual(UsageLog.objects.filter(employee=self.emp1).count(), 2)
        self.goggles.refresh_from_db()
        self.gloves.refresh_from_db()
        self.assertEqual(self.goggles.current_stock, 49)
        self.assertEqual(self.gloves.current_stock, 29)

    def test_submission_redirects_with_prefill_params(self):
        self.login_supervisor()
        response = self.client.post(
            reverse("supervisor_log_submit"), {"employee_id": self.emp1.pk, "item": [self.goggles.pk]}
        )
        self.assertIn("prefill_employee_id", response.url)
        self.assertIn(str(self.emp1.pk), response.url)

    def test_repeated_same_day_logging_not_blocked(self):
        self.login_supervisor()
        for _ in range(3):
            self.client.post(
                reverse("supervisor_log_submit"), {"employee_id": self.emp1.pk, "item": [self.goggles.pk]}
            )
        self.assertEqual(UsageLog.objects.filter(employee=self.emp1, item=self.goggles).count(), 3)
        self.goggles.refresh_from_db()
        self.assertEqual(self.goggles.current_stock, 47)

    def test_stock_allowed_to_go_negative(self):
        self.goggles.current_stock = 1
        self.goggles.save()
        self.login_supervisor()
        self.client.post(reverse("supervisor_log_submit"), {"employee_id": self.emp1.pk, "item": [self.goggles.pk]})
        self.client.post(reverse("supervisor_log_submit"), {"employee_id": self.emp1.pk, "item": [self.goggles.pk]})
        self.goggles.refresh_from_db()
        self.assertEqual(self.goggles.current_stock, -1)

    def test_missing_employee_rejected(self):
        self.login_supervisor()
        response = self.client.post(
            reverse("supervisor_log_submit"), {"employee_id": "", "item": [self.goggles.pk]}, follow=True
        )
        self.assertContains(response, "select a valid employee")
        self.assertEqual(UsageLog.objects.count(), 0)

    def test_malformed_employee_id_does_not_crash(self):
        self.login_supervisor()
        response = self.client.post(
            reverse("supervisor_log_submit"), {"employee_id": "not-a-number", "item": [self.goggles.pk]}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "select a valid employee")

    def test_no_items_rejected(self):
        self.login_supervisor()
        response = self.client.post(
            reverse("supervisor_log_submit"), {"employee_id": self.emp1.pk, "item": []}, follow=True
        )
        self.assertContains(response, "Select at least one item")

    def test_duplicate_item_in_submission_rejected(self):
        self.login_supervisor()
        response = self.client.post(
            reverse("supervisor_log_submit"),
            {"employee_id": self.emp1.pk, "item": [self.goggles.pk, self.goggles.pk]},
            follow=True,
        )
        self.assertContains(response, "more than once")
        self.assertEqual(UsageLog.objects.count(), 0)

    def test_inactive_employee_cannot_be_logged(self):
        self.emp1.is_active = False
        self.emp1.save()
        self.login_supervisor()
        response = self.client.post(
            reverse("supervisor_log_submit"), {"employee_id": self.emp1.pk, "item": [self.goggles.pk]}, follow=True
        )
        self.assertContains(response, "select a valid employee")
        self.assertEqual(UsageLog.objects.count(), 0)

    def test_inactive_item_excluded_from_options(self):
        self.goggles.is_active = False
        self.goggles.save()
        self.login_supervisor()
        response = self.client.get(reverse("supervisor_log_item_options"), {"employee_id": self.emp1.pk})
        names = [i["name"] for i in response.json()["results"]]
        self.assertNotIn("Safety Goggles", names)


class LogEmployeeSearchTests(BaseTestCase):
    def test_search_matches_name_or_code(self):
        self.login_supervisor()
        response = self.client.get(reverse("supervisor_log_employee_search"), {"q": "Ramesh"})
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["code"], "EMP-001")

    def test_inactive_employees_excluded_from_search(self):
        self.emp1.is_active = False
        self.emp1.save()
        self.login_supervisor()
        response = self.client.get(reverse("supervisor_log_employee_search"), {"q": "Ramesh"})
        self.assertEqual(response.json()["results"], [])


class LogItemOptionsStatusTests(BaseTestCase):
    def test_fresh_item_status_is_normal(self):
        self.login_supervisor()
        response = self.client.get(reverse("supervisor_log_item_options"), {"employee_id": self.emp1.pk})
        statuses = {r["name"]: r["status"] for r in response.json()["results"]}
        self.assertEqual(statuses["Safety Goggles"], "normal")

    def test_status_becomes_today_after_logging(self):
        self.login_supervisor()
        self.client.post(reverse("supervisor_log_submit"), {"employee_id": self.emp1.pk, "item": [self.goggles.pk]})
        response = self.client.get(reverse("supervisor_log_item_options"), {"employee_id": self.emp1.pk})
        statuses = {r["name"]: r["status"] for r in response.json()["results"]}
        self.assertEqual(statuses["Safety Goggles"], "today")

    def test_malformed_employee_id_returns_400_not_500(self):
        self.login_supervisor()
        response = self.client.get(reverse("supervisor_log_item_options"), {"employee_id": "abc"})
        self.assertEqual(response.status_code, 400)


class BulkPeriodicAllocateTests(BaseTestCase):
    def test_bulk_periodic_allocate_success(self):
        self.login_supervisor()
        initial_stock = self.goggles.current_stock
        response = self.client.post(reverse("supervisor_bulk_periodic_allocate"))
        self.assertRedirects(response, reverse("supervisor_log"))

        active_emp_count = Employee.objects.filter(is_active=True).count()
        active_item_count = Item.objects.filter(is_active=True).count()
        expected_log_count = active_emp_count * active_item_count

        self.assertEqual(UsageLog.objects.count(), expected_log_count)
        self.goggles.refresh_from_db()
        self.assertEqual(self.goggles.current_stock, initial_stock - active_emp_count)

    def test_bulk_periodic_allocate_disabled_during_cooldown(self):
        self.login_supervisor()
        self.client.post(reverse("supervisor_bulk_periodic_allocate"))

        # Attempt second allocation during active cooldown
        response = self.client.post(reverse("supervisor_bulk_periodic_allocate"))
        self.assertRedirects(response, reverse("supervisor_log"))

        # Verify supervisor log page renders button disabled with cooldown notice
        log_page_resp = self.client.get(reverse("supervisor_log"))
        self.assertContains(log_page_resp, "Bulk Allotment Cooldown Active")


class LogGridSelectorTests(BaseTestCase):
    def test_log_page_renders_grid_container_and_preserved_comments(self):
        self.login_supervisor()
        response = self.client.get(reverse("supervisor_log"))
        self.assertEqual(response.status_code, 200)
        # Verify grid container and toolbar exist
        self.assertContains(response, 'id="item-grid-container"')
        self.assertContains(response, 'id="item-grid"')
        self.assertContains(response, 'id="item-filter-input"')
        self.assertContains(response, 'id="selection-count-badge"')
        # Verify preserved dropdown implementation is commented out
        self.assertContains(response, "PRESERVED DROPDOWN IMPLEMENTATION")
        self.assertContains(response, "PRESERVED DROPDOWN JAVASCRIPT LOGIC")

    def test_item_options_includes_stock_and_colors(self):
        self.login_supervisor()
        response = self.client.get(reverse("supervisor_log_item_options"), {"employee_id": self.emp1.pk})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("colors", data)
        self.assertIn("today", data["colors"])
        self.assertIn("period", data["colors"])
        items = data["results"]
        self.assertTrue(len(items) > 0)
        first_item = items[0]
        self.assertIn("id", first_item)
        self.assertIn("name", first_item)
        self.assertIn("status", first_item)
        self.assertIn("stock", first_item)

    def test_multiple_item_grid_submission(self):
        self.login_supervisor()
        response = self.client.post(
            reverse("supervisor_log_submit"),
            {
                "employee_id": self.emp1.pk,
                "item": [self.goggles.pk, self.earplugs.pk, self.gloves.pk],
            },
        )
        self.assertEqual(UsageLog.objects.filter(employee=self.emp1).count(), 3)
        self.goggles.refresh_from_db()
        self.earplugs.refresh_from_db()
        self.gloves.refresh_from_db()
        self.assertEqual(self.goggles.current_stock, 49)
        self.assertEqual(self.earplugs.current_stock, 199)
        self.assertEqual(self.gloves.current_stock, 29)

    def test_log_submit_invalid_employee(self):
        self.login_supervisor()
        response = self.client.post(
            reverse("supervisor_log_submit"),
            {"employee_id": 99999, "item": [self.goggles.pk]},
            follow=True,
        )
        self.assertContains(response, "Please select a valid employee")

    def test_log_submit_no_items(self):
        self.login_supervisor()
        response = self.client.post(
            reverse("supervisor_log_submit"),
            {"employee_id": self.emp1.pk, "item": []},
            follow=True,
        )
        self.assertContains(response, "Select at least one item to log")

    def test_log_submit_duplicate_items(self):
        self.login_supervisor()
        response = self.client.post(
            reverse("supervisor_log_submit"),
            {"employee_id": self.emp1.pk, "item": [self.goggles.pk, self.goggles.pk]},
            follow=True,
        )
        self.assertContains(response, "The same item was selected more than once")

    def test_log_submit_non_numeric_items(self):
        self.login_supervisor()
        response = self.client.post(
            reverse("supervisor_log_submit"),
            {"employee_id": self.emp1.pk, "item": ["abc", "xyz"]},
            follow=True,
        )
        self.assertContains(response, "One or more selected items are invalid")

    def test_log_item_options_invalid_id(self):
        self.login_supervisor()
        response = self.client.get(reverse("supervisor_log_item_options"), {"employee_id": "abc"})
        self.assertEqual(response.status_code, 400)


