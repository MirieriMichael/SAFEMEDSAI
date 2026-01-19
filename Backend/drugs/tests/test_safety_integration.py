"""
Integration tests for patient safety check functionality.
Uses real Django models and database to test end-to-end behavior.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from drugs.models import Drug, DrugInfo, Profile
from drugs.views import check_patient_safety


class SafetyCheckIntegrationTests(TestCase):
    """Integration tests using real database models."""

    def setUp(self):
        """Set up test data with real User and Profile."""
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

    def test_ulcers_match_with_real_drug_model(self):
        """Test ulcers matching using real Drug and DrugInfo models."""
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
        
        # Assertions
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("ulcers", result["matched_conditions"])
        self.assertIn("matches conditions", result["explanation"].lower())

    def test_bleeding_disorder_match_with_real_models(self):
        """Test bleeding disorder matching with real models."""
        drug = Drug.objects.create(name="Anticoagulant")
        DrugInfo.objects.create(
            drug=drug,
            warnings="Not recommended for patients with bleeding disorders."
        )
        
        self.profile.conditions = ["bleeding disorder"]
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("bleeding disorder", result["matched_conditions"])

    def test_kidney_disease_match_with_real_models(self):
        """Test kidney disease matching with real models."""
        drug = Drug.objects.create(name="Nephrotoxic Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings="Use with caution in patients with kidney issues or kidney disease."
        )
        
        self.profile.conditions = ["kidney disease"]
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("kidney disease", result["matched_conditions"])

    def test_no_matches_with_real_models(self):
        """Test no matches scenario with real models."""
        drug = Drug.objects.create(name="Safe Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings="Take with food. May cause drowsiness."
        )
        
        self.profile.conditions = ["diabetes"]
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Safe")
        self.assertEqual(result["matched_conditions"], [])

    def test_both_allergies_and_conditions_with_real_models(self):
        """Test both allergies and conditions matching with real models."""
        drug = Drug.objects.create(name="Penicillin")
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

    def test_safety_check_in_api_response(self):
        """Test that safety_check appears in API response payload."""
        from drugs.views import ScanAndCheckView
        from rest_framework.test import APIClient
        
        # Create drug
        drug = Drug.objects.create(name="Warfarin")
        DrugInfo.objects.create(
            drug=drug,
            warnings="May cause stomach ulcers and bleeding disorders."
        )
        
        # Set user conditions
        self.profile.conditions = ["ulcers", "bleeding disorder"]
        self.profile.save()
        
        # Create API client and authenticate
        client = APIClient()
        client.force_authenticate(user=self.user)
        
        # Make POST request with drug names
        response = client.post(
            '/api/drugs/scan-and-check/',
            {'drug_names': 'Warfarin'},
            format='multipart'
        )
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertIn('drug_details', response.data)
        
        if response.data.get('drug_details'):
            drug_detail = response.data['drug_details'][0]
            self.assertIn('safety_check', drug_detail)
            safety_check = drug_detail['safety_check']
            self.assertEqual(safety_check['safety_badge'], 'Health Risk')
            self.assertIn('ulcers', safety_check['matched_conditions'])
            self.assertIn('bleeding disorder', safety_check['matched_conditions'])

    def test_empty_profile_returns_safe(self):
        """Test that empty profile returns Safe."""
        drug = Drug.objects.create(name="Test Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings="May cause side effects."
        )
        
        self.profile.allergies = []
        self.profile.conditions = []
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Safe")

    def test_drug_without_druginfo_returns_safe(self):
        """Test that drug without DrugInfo returns Safe."""
        drug = Drug.objects.create(name="Test Drug")
        # No DrugInfo created
        
        self.profile.conditions = ["ulcers"]
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Safe")

    def test_aspirin_ulcers_integration(self):
        """Integration test: Aspirin with ulcers condition should match."""
        # Create Aspirin drug
        aspirin = Drug.objects.create(name="Aspirin")
        DrugInfo.objects.create(
            drug=aspirin,
            warnings="Aspirin should not be taken by individuals with a history of stomach ulcers, bleeding disorders, or other gastrointestinal conditions."
        )
        
        # Set user condition
        self.profile.conditions = ["Ulcers"]
        self.profile.save()
        
        result = check_patient_safety(aspirin, self.user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertIn("Ulcers", result["matched_conditions"])
        self.assertEqual(result["risk_level"], "high")
        self.assertIn("matches", result["explanation"].lower())

    def test_list_conditions_work(self):
        """Test that list conditions work correctly (Profile uses JSONField which stores lists)."""
        drug = Drug.objects.create(name="Test Drug")
        DrugInfo.objects.create(
            drug=drug,
            warnings="May cause stomach ulcers."
        )
        
        # Profile.conditions is a JSONField that stores lists
        self.profile.conditions = ["Ulcers", "Stomach ulcers"]
        self.profile.save()
        
        result = check_patient_safety(drug, self.user)
        
        self.assertEqual(result["safety_badge"], "Health Risk")
        self.assertTrue(len(result["matched_conditions"]) >= 1)

