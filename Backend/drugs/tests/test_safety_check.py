"""
Unit tests for patient safety check functionality.
Tests fuzzy keyword matching for allergies and conditions.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from drugs.models import Drug, DrugInfo, Profile
from drugs.views import check_patient_safety, normalize


class FakeUser:
    """Helper class to create a test user with profile."""
    def __init__(self, allergies=None, conditions=None, is_authenticated=True):
        self.is_authenticated = is_authenticated
        self.profile = FakeProfile(allergies or [], conditions or [])


class FakeProfile:
    """Helper class to simulate user profile."""
    def __init__(self, allergies, conditions):
        self.allergies = allergies if isinstance(allergies, list) else []
        self.conditions = conditions if isinstance(conditions, list) else []


class SafetyCheckTests(TestCase):
    """Test suite for safety check matching logic."""

    def setUp(self):
        """Set up test data."""
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # Create profile for user
        self.profile = Profile.objects.create(
            user=self.user,
            allergies=[],
            conditions=[]
        )

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

    def test_ulcers_match_stomach_ulcers(self):
        """Test that 'ulcers' matches 'stomach ulcers' in warnings."""
        # Create drug with warnings
        drug = Drug.objects.create(name="Test Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings="This drug may cause stomach ulcers and bleeding."
        )
        
        # Set user condition
        self.profile.conditions = ["ulcers"]
        self.profile.save()
        
        # Check safety
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("ulcers", result["matched_conditions"])
        self.assertIn("ulcers", result["explanation"].lower())

    def test_bleeding_disorder_match(self):
        """Test that 'bleeding disorder' matches 'bleeding disorders'."""
        drug = Drug.objects.create(name="Test Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings="Not recommended for patients with bleeding disorders."
        )
        
        self.profile.conditions = ["bleeding disorder"]
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("bleeding disorder", result["matched_conditions"])

    def test_kidney_disease_match(self):
        """Test that 'kidney disease' matches 'kidney issues'."""
        drug = Drug.objects.create(name="Test Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings="Use with caution in patients with kidney issues or kidney disease."
        )
        
        self.profile.conditions = ["kidney disease"]
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("kidney disease", result["matched_conditions"])

    def test_no_matches_returns_safe(self):
        """Test that no matches return 'Safe' badge."""
        drug = Drug.objects.create(name="Test Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings="Take with food. May cause drowsiness."
        )
        
        self.profile.conditions = ["diabetes"]
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Safe")
        self.assertEqual(result["matched_conditions"], [])
        self.assertEqual(result["matched_allergies"], [])

    def test_both_allergies_and_conditions_match(self):
        """Test when both allergies and conditions match."""
        drug = Drug.objects.create(name="Test Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings="Do not take if allergic to penicillin. May worsen stomach ulcers."
        )
        
        self.profile.allergies = ["Penicillin"]
        self.profile.conditions = ["ulcers"]
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("Penicillin", result["matched_allergies"])
        self.assertIn("ulcers", result["matched_conditions"])
        self.assertIn("allergies", result["explanation"].lower())
        self.assertIn("conditions", result["explanation"].lower())

    def test_allergy_match_only(self):
        """Test when only allergies match."""
        drug = Drug.objects.create(name="Test Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings="Contains aspirin. Do not take if allergic to aspirin."
        )
        
        self.profile.allergies = ["Aspirin"]
        self.profile.conditions = []
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("Aspirin", result["matched_allergies"])
        self.assertEqual(result["matched_conditions"], [])

    def test_condition_match_only(self):
        """Test when only conditions match."""
        drug = Drug.objects.create(name="Test Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings="May worsen diabetes. Monitor blood sugar levels."
        )
        
        self.profile.allergies = []
        self.profile.conditions = ["diabetes"]
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("diabetes", result["matched_conditions"])
        self.assertEqual(result["matched_allergies"], [])

    def test_no_allergies_or_conditions_returns_safe(self):
        """Test that empty allergies/conditions return Safe."""
        drug = Drug.objects.create(name="Test Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings="May cause drowsiness."
        )
        
        self.profile.allergies = []
        self.profile.conditions = []
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Safe")

    def test_unauthenticated_user_returns_safe(self):
        """Test that unauthenticated users get Safe badge."""
        drug = Drug.objects.create(name="Test Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings="Test warning"
        )
        
        fake_user = FakeUser(is_authenticated=False)
        result = check_patient_safety(drug, fake_user)
        
        self.assertEqual(result["safety_badge"], "Safe")

    def test_drug_without_warnings_returns_safe(self):
        """Test that drugs without warnings return Safe."""
        drug = Drug.objects.create(name="Test Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings=""
        )
        
        self.profile.conditions = ["ulcers"]
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Safe")

    def test_multiple_conditions_match(self):
        """Test that multiple conditions can match."""
        drug = Drug.objects.create(name="Test Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings="May worsen diabetes and kidney disease. Avoid with liver problems."
        )
        
        self.profile.conditions = ["diabetes", "kidney disease", "liver problems"]
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertEqual(len(result["matched_conditions"]), 3)
        self.assertIn("diabetes", result["matched_conditions"])
        self.assertIn("kidney disease", result["matched_conditions"])
        self.assertIn("liver problems", result["matched_conditions"])

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        drug = Drug.objects.create(name="Test Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings="DIABETES patients should use caution."
        )
        
        self.profile.conditions = ["diabetes"]
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("diabetes", result["matched_conditions"])

    def test_partial_word_matching(self):
        """Test that partial words match correctly."""
        drug = Drug.objects.create(name="Test Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings="May cause allergic reactions in some patients."
        )
        
        self.profile.allergies = ["allergic"]
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("allergic", result["matched_allergies"])

