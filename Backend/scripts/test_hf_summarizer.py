# # safemedsai/safemedsai/scripts/test_hf_summarizer.py
# import os
# import sys
# from pathlib import Path

# # ---- Adjust paths so Python can import your Django app modules ----
# # This file is in .../safemedsai/scripts/
# HERE = Path(__file__).resolve()
# PROJECT_ROOT = HERE.parents[1]  # points to .../safemedsai (the inner safemedsai folder)
# BACKEND_DIR = PROJECT_ROOT / "backend"  # .../safemedsai/backend

# # Add project root and backend to sys.path so "drugs" package can be imported
# for p in (str(PROJECT_ROOT), str(BACKEND_DIR)):
#     if p not in sys.path:
#         sys.path.insert(0, p)

# # Optional: if you later want to import Django models directly, uncomment:
# # os.environ.setdefault("DJANGO_SETTINGS_MODULE", "safemedsai.settings")
# # import django
# # django.setup()

# from drugs.hf_summarizer import summarize_structured  # now should import

# sample = """Paste a sample OpenFDA field here (adverse_reactions, warnings, dosage...). 
# For example copy the long text you saw for Lumigan or Warfarin..."""

# res = summarize_structured(sample)
# print("DEBUG:", res.get("debug"))
# print("Overview:", res.get("overview"))
# print("Side effects:", res.get("side_effects"))
# print("Warnings:", res.get("warnings"))
# print("Interactions:", res.get("interactions"))
# print("Administration:", res.get("administration"))
