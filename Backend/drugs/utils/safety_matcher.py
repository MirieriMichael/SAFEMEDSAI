"""
Robust safety matching utilities for patient safety checks.
Handles normalization, synonyms, and fuzzy matching.
"""
import re
import json
import logging

logger = logging.getLogger(__name__)

# Medical synonyms map for better matching
SYNONYMS = {
    "ulcer": ["ulcer", "stomach ulcer", "peptic ulcer", "gastric ulcer"],
    "bleeding": ["bleed", "bleeding", "hemorrhage", "hemorrhagic"],
    "kidney": ["kidney", "renal", "nephro"],
    "liver": ["liver", "hepatic", "hepat"],
    "heart": ["heart", "cardiac", "cardio"],
    "diabetes": ["diabetes", "diabetic", "blood sugar"],
    "asthma": ["asthma", "asthmatic", "breathing"],
}

# Stop words that are too generic to match
STOP_WORDS = {"pain", "issue", "problem", "disorder", "disease", "condition"}


def normalize_term(text):
    """
    Normalizes a term for keyword matching.
    
    Steps:
    1. Lowercase
    2. Remove punctuation
    3. Collapse multiple spaces
    4. Remove trailing plural 's' (basic stemming)
    5. Trim and return normalized token set (words)
    
    Example: "Stomach ulcers!" -> ["stomach", "ulcer"]
    
    Args:
        text: String to normalize
        
    Returns:
        List of normalized tokens (words)
    """
    if not text or not isinstance(text, str):
        return []
    
    # Lowercase
    text = text.lower()
    
    # Remove punctuation
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Split into words
    words = text.split()
    
    # Remove trailing 's' (basic stemming) and filter short words
    normalized = []
    for word in words:
        word = word.strip()
        if len(word) < 2:  # Skip very short words
            continue
        # Remove trailing 's' for plural handling
        if len(word) > 1 and word.endswith('s'):
            word = word[:-1]
        normalized.append(word)
    
    return normalized


def normalize_user_terms(terms):
    """
    Normalizes user profile terms (allergies/conditions) to a Python list of strings.
    
    Handles:
    - Python lists
    - JSON strings
    - Comma-separated strings
    - Empty/null values
    
    Args:
        terms: Can be list, JSON string, comma-separated string, or None
        
    Returns:
        List of trimmed, non-empty strings
    """
    if not terms:
        return []
    
    # If already a list, return it (after cleaning)
    if isinstance(terms, list):
        result = []
        for item in terms:
            if isinstance(item, str):
                item = item.strip()
                if item:
                    result.append(item)
        return result
    
    # If it's a string, try to parse it
    if isinstance(terms, str):
        terms = terms.strip()
        if not terms:
            return []
        
        # Try JSON first (in case it's a JSON string)
        try:
            parsed = json.loads(terms)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Fall back to comma-separated string
        items = [item.strip() for item in terms.split(',') if item.strip()]
        return items
    
    # For other types, convert to string and try
    return [str(terms).strip()] if str(terms).strip() else []


def check_term_match(user_term, drug_text_normalized, synonyms_map=None):
    """
    Checks if a user term matches drug text using conservative matching rules.
    
    Matching strategy:
    a) The normalized user token sequence appears as a contiguous substring
    b) Any normalized user token is present in the normalized drug token list
    c) Any synonym from the synonyms map appears in the drug text
    
    Args:
        user_term: Original user term (e.g., "Ulcers")
        drug_text_normalized: List of normalized tokens from drug text
        synonyms_map: Dictionary mapping terms to synonym lists
        
    Returns:
        True if match found, False otherwise
    """
    if not user_term or not drug_text_normalized:
        return False
    
    # Normalize user term
    user_tokens = normalize_term(user_term)
    if not user_tokens:
        return False
    
    # Check for too generic words (stop words)
    if len(user_tokens) == 1 and user_tokens[0] in STOP_WORDS:
        return False
    
    # Strategy a: Check if user token sequence appears as contiguous substring
    user_text = ' '.join(user_tokens)
    drug_text = ' '.join(drug_text_normalized)
    if user_text in drug_text:
        return True
    
    # Strategy b: Check if any user token appears in drug tokens
    for token in user_tokens:
        if len(token) >= 3 and token in drug_text_normalized:  # Avoid single-letter noise
            return True
    
    # Strategy c: Check synonyms
    if synonyms_map:
        for token in user_tokens:
            if token in synonyms_map:
                for synonym in synonyms_map[token]:
                    synonym_tokens = normalize_term(synonym)
                    # Check if any synonym token appears in drug text
                    for syn_token in synonym_tokens:
                        if len(syn_token) >= 3 and syn_token in drug_text_normalized:
                            return True
    
    return False


def extract_drug_text(drug):
    """
    Extracts all relevant text from a drug for safety matching.
    
    Checks (in order):
    1. drug.druginfo.warnings
    2. drug.druginfo.contraindications
    3. drug.druginfo.side_effects
    4. drug.warnings, drug.contraindications, drug.side_effects (top-level)
    
    Args:
        drug: Drug model instance or dict
        
    Returns:
        Tuple of (combined_text, source_fields_dict) where source_fields_dict
        contains the actual text from each field (for confidence scoring)
    """
    warnings = ""
    contraindications = ""
    side_effects = ""
    
    source_fields = {
        'warnings': "",
        'contraindications': "",
        'side_effects': ""
    }
    
    if isinstance(drug, dict):
        # Check nested druginfo first (most reliable)
        druginfo = drug.get('druginfo', {})
        if isinstance(druginfo, dict):
            warnings = str(druginfo.get('warnings', '') or '')
            contraindications = str(druginfo.get('contraindications', '') or '')
            side_effects = str(druginfo.get('side_effects', '') or '')
        
        # Fall back to top-level fields if druginfo didn't have them
        if not warnings:
            warnings = str(drug.get('warnings', '') or '')
        if not contraindications:
            contraindications = str(drug.get('contraindications', '') or '')
        if not side_effects:
            side_effects = str(drug.get('side_effects', '') or '')
    else:
        # Drug is a model instance
        try:
            druginfo = getattr(drug, 'druginfo', None)
            if druginfo:
                warnings = str(getattr(druginfo, 'warnings', '') or '')
                contraindications = str(getattr(druginfo, 'contraindications', '') or '')
                side_effects = str(getattr(druginfo, 'side_effects', '') or '')
        except Exception as e:
            logger.debug(f"Error accessing druginfo for {drug}: {e}")
    
    # Store individual fields
    source_fields['warnings'] = warnings
    source_fields['contraindications'] = contraindications
    source_fields['side_effects'] = side_effects
    
    # Combine all text for matching
    combined = f"{warnings} {contraindications} {side_effects}".strip()
    
    return combined, source_fields

