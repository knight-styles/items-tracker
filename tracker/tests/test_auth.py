from django.core.cache import cache
from django.urls import reverse

from .base import BaseTestCase


class LoginTests(BaseTestCase):
    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_successful_admin_login_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("login"), {"username": "admin1", "password": "AdminPass123!"}, follow=True
        )
        self.assertRedirects(response, reverse("admin_dashboard"))

    def test_successful_supervisor_login_redirects_to_log(self):
        self.client.post(reverse("login"), {"username": "super1", "password": "SuperPass123!"})
        response = self.client.get(reverse("dashboard_redirect"))
        self.assertRedirects(response, reverse("supervisor_log"))

    def test_wrong_password_shows_generic_error(self):
        response = self.client.post(reverse("login"), {"username": "admin1", "password": "wrong"})
        self.assertContains(response, "Invalid username or password")

    def test_deactivated_account_shows_specific_message(self):
        self.supervisor.is_active = False
        self.supervisor.save()
        response = self.client.post(reverse("login"), {"username": "super1", "password": "SuperPass123!"})
        self.assertContains(response, "This account has been deactivated")

    def test_deactivated_account_wrong_password_does_not_leak_status(self):
        self.supervisor.is_active = False
        self.supervisor.save()
        response = self.client.post(reverse("login"), {"username": "super1", "password": "WrongOne"})
        self.assertContains(response, "Invalid username or password")
        self.assertNotContains(response, "deactivated")

    def test_logout_get_rejected_with_405(self):
        """Logout must be POST-only to prevent logout CSRF attacks (BUG-6)."""
        self.login_admin()
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)

    def test_logout_post_redirects_to_login(self):
        self.login_admin()
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))

    def test_unauthenticated_user_redirected_to_login(self):
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)


class LoginRateLimitTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def test_lockout_after_repeated_failures(self):
        for _ in range(5):
            self.client.post(reverse("login"), {"username": "super1", "password": "wrong"})
        response = self.client.post(reverse("login"), {"username": "super1", "password": "wrong"})
        self.assertContains(response, "Too many failed login attempts")

    def test_lockout_blocks_even_correct_password(self):
        for _ in range(5):
            self.client.post(reverse("login"), {"username": "super1", "password": "wrong"})
        response = self.client.post(reverse("login"), {"username": "super1", "password": "SuperPass123!"})
        self.assertContains(response, "Too many failed login attempts")

    def test_successful_login_clears_attempt_counter(self):
        self.client.post(reverse("login"), {"username": "super1", "password": "wrong"})
        self.client.post(reverse("login"), {"username": "super1", "password": "wrong"})
        response = self.client.post(
            reverse("login"), {"username": "super1", "password": "SuperPass123!"}, follow=True
        )
        self.assertRedirects(response, reverse("supervisor_log"))
        self.client.post(reverse("logout"))
        # subsequent failed attempts should start counting from zero again
        for _ in range(4):
            r = self.client.post(reverse("login"), {"username": "super1", "password": "wrong"})
        self.assertContains(r, "Invalid username or password")
