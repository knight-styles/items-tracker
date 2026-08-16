from django.test import TestCase
from tracker.models import Employee, Item
from tracker.search_utils import fuzzy_filter_and_rank, damerau_levenshtein_distance, normalize_text


class FuzzySearchTests(TestCase):
    def setUp(self):
        self.emp1 = Employee.objects.create(name="Rahul Kumar", code="EMP-101", is_active=True)
        self.emp2 = Employee.objects.create(name="John Doe", code="EMP-102", is_active=True)
        self.emp3 = Employee.objects.create(name="Safety Manager", code="EMP-103", is_active=True)
        self.emp4 = Employee.objects.create(name="Employee Alpha", code="EMP-104", is_active=True)

    def test_damerau_levenshtein_distance(self):
        self.assertEqual(damerau_levenshtein_distance("employe", "employee"), 1)
        self.assertEqual(damerau_levenshtein_distance("emoloyee", "employee"), 1)
        self.assertEqual(damerau_levenshtein_distance("saftey", "safety"), 1)
        self.assertEqual(damerau_levenshtein_distance("same", "same"), 0)

    def test_normalize_text(self):
        self.assertEqual(normalize_text("  John   Doe  "), "john doe")

    def test_exact_match_ranking(self):
        results, is_fuzzy = fuzzy_filter_and_rank(Employee.objects.all(), "John", ["name", "code"])
        self.assertFalse(is_fuzzy)
        self.assertEqual(results[0], self.emp2)

    def test_case_insensitive_match(self):
        results, is_fuzzy = fuzzy_filter_and_rank(Employee.objects.all(), "jOhN", ["name", "code"])
        self.assertFalse(is_fuzzy)
        self.assertEqual(results[0], self.emp2)

    def test_prefix_match(self):
        results, is_fuzzy = fuzzy_filter_and_rank(Employee.objects.all(), "rah", ["name", "code"])
        self.assertFalse(is_fuzzy)
        self.assertIn(self.emp1, results)

    def test_fuzzy_match_typos(self):
        # "employyee" -> extra character fuzzy match
        results, is_fuzzy = fuzzy_filter_and_rank(Employee.objects.all(), "employyee", ["name", "code"])
        self.assertTrue(is_fuzzy)
        self.assertIn(self.emp4, results)

        # "emoloyee" -> swapped character
        results, is_fuzzy = fuzzy_filter_and_rank(Employee.objects.all(), "emoloyee", ["name", "code"])
        self.assertTrue(is_fuzzy)
        self.assertIn(self.emp4, results)

        # "saftey" -> spelling mistake
        results, is_fuzzy = fuzzy_filter_and_rank(Employee.objects.all(), "saftey", ["name", "code"])
        self.assertTrue(is_fuzzy)
        self.assertIn(self.emp3, results)

    def test_code_number_search(self):
        results, is_fuzzy = fuzzy_filter_and_rank(Employee.objects.all(), "102", ["name", "code"])
        self.assertFalse(is_fuzzy)
        self.assertEqual(results[0], self.emp2)
