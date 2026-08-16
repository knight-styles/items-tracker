"""
Q-7: Verify that all model changes have corresponding migrations.
Catches the common failure mode of changing a model field without running
makemigrations before committing -- which would pass all other tests but
then crash on first deployment.
"""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase


class MigrationIntegrityTest(TestCase):
    def test_no_missing_migrations(self):
        """
        Fails if any model change has been made without a corresponding
        migration. Equivalent to: python manage.py makemigrations --check
        """
        out = StringIO()
        try:
            call_command(
                "makemigrations",
                "--check",
                "--dry-run",
                verbosity=0,
                stdout=out,
                stderr=out,
            )
        except SystemExit as e:
            self.fail(
                "There are model changes without a migration. "
                "Run: python manage.py makemigrations\n"
                f"Details: {out.getvalue()}"
            )
