# Patient Safety Matching System

## Overview

The safety matching system compares user profile conditions and allergies against drug warnings, contraindications, and side effects to identify potential health risks.

## Key Components

### 1. Normalization (`normalize_term`)

Normalizes text for matching:
- Lowercases all text
- Removes punctuation
- Collapses multiple spaces
- Removes trailing 's' (basic stemming for plurals)
- Returns list of normalized tokens

Example: `"Stomach ulcers!"` → `["stomach", "ulcer"]`

### 2. User Term Normalization (`normalize_user_terms`)

Handles various input formats:
- Python lists: `["Ulcers", "Diabetes"]`
- JSON strings: `'["Ulcers", "Diabetes"]'`
- Comma-separated strings: `"Ulcers, Diabetes"`
- Empty/null values

Always returns a clean list of trimmed strings.

### 3. Matching Strategy (`check_term_match`)

Uses three strategies (any one can trigger a match):

**a) Contiguous Substring Match**
- Normalized user token sequence appears as substring in normalized drug text
- Example: `"stomach ulcer"` matches `"history of stomach ulcer"`

**b) Token Intersection**
- Any normalized user token appears in normalized drug token list
- Minimum token length: 3 characters (avoids single-letter noise)
- Example: `"ulcer"` matches `"stomach ulcers"` (after normalization)

**c) Synonym Matching**
- Uses medical synonyms map
- Example: `"ulcer"` matches `"peptic ulcer"` via synonym expansion

### 4. Drug Text Extraction (`extract_drug_text`)

Extracts text from all relevant drug fields:
1. `drug.druginfo.warnings` (highest priority)
2. `drug.druginfo.contraindications`
3. `drug.druginfo.side_effects`
4. Top-level fields (fallback)

Returns combined text and individual field contents for confidence scoring.

## Synonyms Map

Current synonyms:
- `ulcer`: ["ulcer", "stomach ulcer", "peptic ulcer", "gastric ulcer"]
- `bleeding`: ["bleed", "bleeding", "hemorrhage", "hemorrhagic"]
- `kidney`: ["kidney", "renal", "nephro"]
- `liver`: ["liver", "hepatic", "hepat"]
- `heart`: ["heart", "cardiac", "cardio"]
- `diabetes`: ["diabetes", "diabetic", "blood sugar"]
- `asthma`: ["asthma", "asthmatic", "breathing"]

## Risk Levels

- **High Risk** (`safety_badge: "Health Risk"`, `risk_level: "high"`)
  - Match found in `warnings` or `contraindications`
  
- **Medium Risk** (`safety_badge: "Use With Caution"`, `risk_level: "medium"`)
  - Match found only in `side_effects`

- **Low Risk** (`safety_badge: "Safe"`, `risk_level: "low"`)
  - No matches found

## Stop Words

Generic words that are too common to match reliably:
- "pain", "issue", "problem", "disorder", "disease", "condition"

These are filtered out when they appear as single-token conditions.

## Usage

```python
from drugs.views import check_patient_safety

result = check_patient_safety(drug, user)

# Result structure:
{
    "safety_badge": "Health Risk" | "Use With Caution" | "Safe",
    "matched_allergies": ["Aspirin", ...],
    "matched_conditions": ["Ulcers", ...],
    "explanation": "Detailed explanation...",
    "risk_level": "high" | "medium" | "low"
}
```

## Example: Aspirin + Ulcers

**User Profile:**
- Conditions: `["Ulcers"]` or `["Stomach ulcers"]`

**Aspirin Warnings:**
- "Aspirin should not be taken by individuals with a history of stomach ulcers..."

**Match Process:**
1. Normalize user term: `"Ulcers"` → `["ulcer"]`
2. Normalize drug text: `"stomach ulcers"` → `["stomach", "ulcer"]`
3. Token intersection: `"ulcer"` in `["stomach", "ulcer"]` → **MATCH**
4. Result: `safety_badge: "Health Risk"`, `matched_conditions: ["Ulcers"]`

## Testing

Run tests:
```bash
python manage.py test drugs.tests.test_safety_check
python manage.py test drugs.tests.test_safety_integration
```

Key test cases:
- `test_aspirin_ulcers_match` - Verifies Aspirin/ulcers matching
- `test_ulcers_matches_stomach_ulcers` - Basic fuzzy matching
- `test_side_effects_only_match` - Risk level differentiation



