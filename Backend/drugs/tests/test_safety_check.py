"""
Unit tests for patient safety check functionality.
Tests fuzzy keyword matching for allergies and conditions.
Uses FakeUser helper to avoid database dependencies.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from drugs.models import Drug, DrugInfo, Profile
from drugs.views import check_patient_safety, normalize
from .helpers import FakeUser, FakeProfile


class SafetyCheckUnitTests(TestCase):
    """Unit tests using FakeUser (no database required)."""

    def test_ulcers_matches_stomach_ulcers(self):
        """Test that 'ulcers' matches 'stomach ulcers' in warnings."""
        # Create a fake drug dict with warnings (matches function's dict handling)
        fake_drug = {
            'warnings': "This drug may cause stomach ulcers and bleeding.",
            'contraindications': ""
        }
        
        # Create fake user with condition
        fake_user = FakeUser(conditions=["ulcers"])
        
        # Check safety
        result = check_patient_safety(fake_drug, fake_user)
        
        # Assertions
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("ulcers", result["matched_conditions"])
        self.assertEqual(result["matched_allergies"], [])
        self.assertIn("matches conditions", result["explanation"].lower())

    def test_bleeding_disorder_matches_bleeding_disorders(self):
        """Test that 'bleeding disorder' matches 'bleeding disorders'."""
        fake_drug = {
            'warnings': "Not recommended for patients with bleeding disorders.",
            'contraindications': ""
        }
        fake_user = FakeUser(conditions=["bleeding disorder"])
        
        result = check_patient_safety(fake_drug, fake_user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("bleeding disorder", result["matched_conditions"])
        self.assertIn("matches conditions", result["explanation"].lower())

    def test_kidney_disease_matches_kidney_issues(self):
        """Test that 'kidney disease' matches 'kidney issues'."""
        fake_drug = {
            'warnings': "Use with caution in patients with kidney issues or kidney disease.",
            'contraindications': ""
        }
        fake_user = FakeUser(conditions=["kidney disease"])
        
        result = check_patient_safety(fake_drug, fake_user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("kidney disease", result["matched_conditions"])
        self.assertIn("matches conditions", result["explanation"].lower())

    def test_no_matches_returns_safe(self):
        """Test that no matches return 'Safe' badge."""
        fake_drug = {
            'warnings': "Take with food. May cause drowsiness.",
            'contraindications': ""
        }
        fake_user = FakeUser(conditions=["diabetes"])
        
        result = check_patient_safety(fake_drug, fake_user)
        
        self.assertEqual(result["safety_badge"], "Safe")
        self.assertEqual(result["matched_conditions"], [])
        self.assertEqual(result["matched_allergies"], [])
        self.assertIn("no known risks", result["explanation"].lower())

    def test_both_allergies_and_conditions_match(self):
        """Test when both allergies and conditions match."""
        fake_drug = {
            'warnings': "Do not take if allergic to penicillin. May worsen stomach ulcers.",
            'contraindications': ""
        }
        fake_user = FakeUser(
            allergies=["Penicillin"],
            conditions=["ulcers"]
        )
        
        result = check_patient_safety(fake_drug, fake_user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("Penicillin", result["matched_allergies"])
        self.assertIn("ulcers", result["matched_conditions"])
        self.assertIn("matches conditions", result["explanation"].lower())

    def test_allergy_match_only(self):
        """Test when only allergies match."""
        fake_drug = {
            'warnings': "Contains aspirin. Do not take if allergic to aspirin.",
            'contraindications': ""
        }
        fake_user = FakeUser(
            allergies=["Aspirin"],
            conditions=[]
        )
        
        result = check_patient_safety(fake_drug, fake_user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("Aspirin", result["matched_allergies"])
        self.assertEqual(result["matched_conditions"], [])

    def test_condition_match_only(self):
        """Test when only conditions match."""
        fake_drug = {
            'warnings': "May worsen diabetes. Monitor blood sugar levels.",
            'contraindications': ""
        }
        fake_user = FakeUser(
            allergies=[],
            conditions=["diabetes"]
        )
        
        result = check_patient_safety(fake_drug, fake_user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("diabetes", result["matched_conditions"])
        self.assertEqual(result["matched_allergies"], [])

    def test_unauthenticated_user_returns_safe(self):
        """Test that unauthenticated users get Safe badge."""
        fake_drug = {
            'warnings': "Test warning",
            'contraindications': ""
        }
        fake_user = FakeUser(is_authenticated=False)
        
        result = check_patient_safety(fake_drug, fake_user)
        
        self.assertEqual(result["safety_badge"], "Safe")

    def test_drug_without_warnings_returns_safe(self):
        """Test that drugs without warnings return Safe."""
        fake_drug = {
            'warnings': "",
            'contraindications': ""
        }
        fake_user = FakeUser(conditions=["ulcers"])
        
        result = check_patient_safety(fake_drug, fake_user)
        
        self.assertEqual(result["safety_badge"], "Safe")

    def test_normalize_function(self):
        """Test the normalize helper function."""
        # Test basic normalization
        result = normalize("Stomach Ulcers!")
        self.assertIn("stomach", result)
        self.assertIn("ulcer", result)  # Should remove 's' and punctuation
        
        # Test plural handling
        result = normalize("bleeding disorders")
        self.assertIn("bleeding", result)
        self.assertIn("disorder", result)  # Should remove 's'
        
        # Test punctuation removal
        result = normalize("kidney disease, liver issues.")
        self.assertIn("kidney", result)
        self.assertIn("disease", result)
        self.assertIn("liver", result)
        self.assertIn("issue", result)

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        fake_drug = {
            'warnings': "DIABETES patients should use caution.",
            'contraindications': ""
        }
        fake_user = FakeUser(conditions=["diabetes"])
        
        result = check_patient_safety(fake_drug, fake_user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("diabetes", result["matched_conditions"])

    def test_multiple_conditions_match(self):
        """Test that multiple conditions can match."""
        fake_drug = {
            'warnings': "May worsen diabetes and kidney disease. Avoid with liver problems.",
            'contraindications': ""
        }
        fake_user = FakeUser(conditions=["diabetes", "kidney disease", "liver problems"])
        
        result = check_patient_safety(fake_drug, fake_user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertEqual(len(result["matched_conditions"]), 3)
        self.assertIn("diabetes", result["matched_conditions"])
        self.assertIn("kidney disease", result["matched_conditions"])
        self.assertIn("liver problems", result["matched_conditions"])

    def test_aspirin_ulcers_match(self):
        """Test that Aspirin warnings match user profile with 'Ulcers' or 'Stomach ulcers'."""
        # Aspirin typically has warnings like "should not be taken by individuals with a history of stomach ulcers"
        fake_drug = {
            'warnings': "Aspirin should not be taken by individuals with a history of stomach ulcers, bleeding disorders, or other gastrointestinal conditions.",
            'contraindications': "",
            'side_effects': ""
        }
        
        # Test with "Ulcers"
        fake_user = FakeUser(conditions=["Ulcers"])
        result = check_patient_safety(fake_drug, fake_user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("Ulcers", result["matched_conditions"])
        self.assertIn("matches", result["explanation"].lower())
        
        # Test with "Stomach ulcers"
        fake_user2 = FakeUser(conditions=["Stomach ulcers"])
        result2 = check_patient_safety(fake_drug, fake_user2)
        
        self.assertEqual(result2["safety_badge"], "Health Risk")
        self.assertIn("Stomach ulcers", result2["matched_conditions"])

    def test_comma_separated_conditions(self):
        """Test that comma-separated condition strings are parsed correctly."""
        fake_drug = {
            'warnings': "May cause stomach ulcers and bleeding.",
            'contraindications': ""
        }
        
        # Simulate comma-separated string input
        from drugs.utils.safety_matcher import normalize_user_terms
        conditions = normalize_user_terms("Ulcers, bleeding disorder, diabetes")
        
        fake_user = FakeUser(conditions=conditions)
        result = check_patient_safety(fake_drug, fake_user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertTrue(len(result["matched_conditions"]) >= 1)

    def test_side_effects_only_match(self):
        """Test that matches only in side_effects return 'Use With Caution'."""
        fake_drug = {
            'warnings': "",
            'contraindications': "",
            'side_effects': "May cause stomach ulcers in some patients."
        }
        fake_user = FakeUser(conditions=["ulcers"])
        
        result = check_patient_safety(fake_drug, fake_user)
        
        self.assertEqual(result["safety_badge"], "Use With Caution")
        self.assertIn("ulcers", result["matched_conditions"])
        self.assertEqual(result["risk_level"], "medium")

    def test_risk_level_high_for_warnings(self):
        """Test that matches in warnings return high risk level."""
        fake_drug = {
            'warnings': "Should not be taken by patients with stomach ulcers.",
            'contraindications': "",
            'side_effects': ""
        }
        fake_user = FakeUser(conditions=["ulcers"])
        
        result = check_patient_safety(fake_drug, fake_user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertEqual(result["risk_level"], "high")

