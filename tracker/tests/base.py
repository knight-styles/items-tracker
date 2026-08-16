from django.core.cache import cache
from django.test import TestCase

from tracker.models import AppSettings, Employee, Item, User


class BaseTestCase(TestCase):
    """Common fixtures: one Admin, one Supervisor, two employees, three items."""

    def setUp(self):
        cache.clear()  # avoid login rate-limit state leaking between tests

        self.admin = User.objects.create_superuser("admin1", "admin1@example.com", "AdminPass123!")
        self.admin.role = User.Role.ADMIN
        self.admin.save()

        self.supervisor = User.objects.create_user("super1", "super1@example.com", "SuperPass123!")
        self.supervisor.role = User.Role.SUPERVISOR
        self.supervisor.created_by = self.admin
        self.supervisor.save()

        self.emp1 = Employee.objects.create(name="Ramesh Kumar", code="EMP-001", created_by=self.admin, updated_by=self.admin)
        self.emp2 = Employee.objects.create(name="Suresh Patel", code="EMP-002", created_by=self.admin, updated_by=self.admin)

        self.goggles = Item.objects.create(name="Safety Goggles", current_stock=50, created_by=self.admin, updated_by=self.admin)
        self.earplugs = Item.objects.create(name="Ear Plugs", current_stock=200, created_by=self.admin, updated_by=self.admin)
        self.gloves = Item.objects.create(name="Work Gloves", current_stock=30, created_by=self.admin, updated_by=self.admin)

        self.settings = AppSettings.load()

    def login_admin(self):
        self.client.login(username="admin1", password="AdminPass123!")

    def login_supervisor(self):
        self.client.login(username="super1", password="SuperPass123!")
