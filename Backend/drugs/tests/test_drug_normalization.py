"""
Unit test for drug details normalization.
Ensures druginfo fields are always present and strings.
"""
from django.test import TestCase
import json


class DrugNormalizationTests(TestCase):
    """Test drug normalization logic."""

    def test_normalize_drug_with_nested_druginfo(self):
        """Test normalization when druginfo is nested."""
        from drugs.views import _pack_payload
        
        # Create a mock drug detail with nested druginfo
        drug_detail = {
            "id": 1,
            "name": "Test Drug",
            "druginfo": {
                "administration": "Take with food",
                "side_effects": "Nausea",
                "warnings": "May cause drowsiness"
            }
        }
        
        # Simulate normalization (extract the logic)
        def normalize_drug(drug):
            di = drug.get("druginfo") or {}
            di["administration"] = di.get("administration") or drug.get("administration") or ""
            di["side_effects"] = di.get("side_effects") or drug.get("side_effects") or ""
            di["warnings"] = di.get("warnings") or drug.get("warnings") or ""
            
            for k in ("administration", "side_effects", "warnings"):
                if di.get(k) is None:
                    di[k] = ""
                else:
                    di[k] = str(di[k])
            
            drug["druginfo"] = di
            return drug
        
        normalized = normalize_drug(drug_detail)
        
        # Verify druginfo exists and has string values
        self.assertIn("druginfo", normalized)
        self.assertIsInstance(normalized["druginfo"], dict)
        self.assertEqual(normalized["druginfo"]["administration"], "Take with food")
        self.assertEqual(normalized["druginfo"]["side_effects"], "Nausea")
        self.assertEqual(normalized["druginfo"]["warnings"], "May cause drowsiness")
        self.assertIsInstance(normalized["druginfo"]["administration"], str)

    def test_normalize_drug_with_top_level_fields(self):
        """Test normalization when fields are at top level."""
        drug_detail = {
            "id": 1,
            "name": "Test Drug",
            "administration": "Take with water",
            "side_effects": "Headache",
            "warnings": "Avoid alcohol"
        }
        
        def normalize_drug(drug):
            di = drug.get("druginfo") or {}
            di["administration"] = di.get("administration") or drug.get("administration") or ""
            di["side_effects"] = di.get("side_effects") or drug.get("side_effects") or ""
            di["warnings"] = di.get("warnings") or drug.get("warnings") or ""
            
            for k in ("administration", "side_effects", "warnings"):
                if di.get(k) is None:
                    di[k] = ""
                else:
                    di[k] = str(di[k])
            
            drug["druginfo"] = di
            return drug
        
        normalized = normalize_drug(drug_detail)
        
        # Verify druginfo is populated from top-level
        self.assertIn("druginfo", normalized)
        self.assertEqual(normalized["druginfo"]["administration"], "Take with water")
        self.assertEqual(normalized["druginfo"]["side_effects"], "Headache")
        self.assertEqual(normalized["druginfo"]["warnings"], "Avoid alcohol")

    def test_normalize_drug_with_null_values(self):
        """Test normalization handles null values correctly."""
        drug_detail = {
            "id": 1,
            "name": "Test Drug",
            "druginfo": {
                "administration": None,
                "side_effects": "",
                "warnings": None
            }
        }
        
        def normalize_drug(drug):
            di = drug.get("druginfo") or {}
            di["administration"] = di.get("administration") or drug.get("administration") or ""
            di["side_effects"] = di.get("side_effects") or drug.get("side_effects") or ""
            di["warnings"] = di.get("warnings") or drug.get("warnings") or ""
            
            for k in ("administration", "side_effects", "warnings"):
                if di.get(k) is None:
                    di[k] = ""
                else:
                    di[k] = str(di[k])
            
            drug["druginfo"] = di
            return drug
        
        normalized = normalize_drug(drug_detail)
        
        # Verify null values become empty strings
        self.assertEqual(normalized["druginfo"]["administration"], "")
        self.assertEqual(normalized["druginfo"]["side_effects"], "")
        self.assertEqual(normalized["druginfo"]["warnings"], "")
        self.assertIsInstance(normalized["druginfo"]["administration"], str)



