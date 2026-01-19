# Drug Safety Check Tests

This directory contains unit and integration tests for the patient safety check functionality.

## Test Files

- `test_safety_check.py` - Unit tests using FakeUser helper (no database required)
- `test_safety_integration.py` - Integration tests using real Django models
- `helpers.py` - Test helper classes (FakeUser, FakeProfile, normalize function)
- `test_drug_normalization.py` - Tests for drug details normalization

## Running Tests

### Run all safety check tests:
```bash
python manage.py test drugs.tests.test_safety_check
python manage.py test drugs.tests.test_safety_integration
```

### Run all tests in the drugs app:
```bash
python manage.py test drugs.tests
```

### Run a specific test:
```bash
python manage.py test drugs.tests.test_safety_check.SafetyCheckUnitTests.test_ulcers_matches_stomach_ulcers
```

## Test Coverage

The tests cover:
1. ✅ "ulcers" → matches "stomach ulcers"
2. ✅ "bleeding disorder" → matches "bleeding disorders"
3. ✅ "kidney disease" → matches "kidney issues"
4. ✅ No matches → `safety_badge` == "Safe"
5. ✅ Both allergies & conditions match → both fields reported

## Helper Classes

- `FakeUser` - Creates a test user with profile (no DB)
- `FakeProfile` - Simulates user profile with allergies/conditions
- `normalize()` - Text normalization function for matching

## Notes

- Unit tests use `FakeUser` to avoid database dependencies
- Integration tests use real Django models and require database
- All tests are isolated and clean up after themselves



