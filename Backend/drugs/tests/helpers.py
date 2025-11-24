"""
Test helpers for patient safety check tests.
Provides FakeUser and FakeProfile classes for unit testing without database.
"""
import re


class FakeProfile:
    """Helper class to simulate user profile for testing."""
    def __init__(self, allergies=None, conditions=None):
        self.allergies = allergies if allergies is not None else []
        self.conditions = conditions if conditions is not None else []


class FakeUser:
    """Helper class to create a test user with profile (no DB required)."""
    def __init__(self, allergies=None, conditions=None, is_authenticated=True):
        self.is_authenticated = is_authenticated
        self.profile = FakeProfile(allergies or [], conditions or [])


def normalize(text):
    """
    Normalizes text for keyword matching (matches implementation in views.py).
    Used in tests to verify matching logic.
    """
    if not text or not isinstance(text, str):
        return []
    
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    words = text.split()
    words = [w[:-1] if w.endswith('s') else w for w in words]
    return words

