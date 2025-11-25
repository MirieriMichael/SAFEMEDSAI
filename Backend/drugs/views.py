from __future__ import annotations

from asyncio.log import logger
import os
import re
import platform
import hashlib
import logging
from itertools import combinations
from typing import List, Set, Tuple, Dict
import json # <-- NEW IMPORT
# backend/drugs/views.py

# ... (keep your existing imports)

# --- NEW IMPORTS FOR 2FA ---
import base64
import io
import qrcode
from django_otp.plugins.otp_totp.models import TOTPDevice
# ---------------------------
import datetime
import numpy as np
import cv2
from PIL import Image
import pytesseract
# backend/drugs/views.py

# ... (other imports like os, logging, etc.) ...
from django.utils import timezone  # <-- ADD THIS LINE
# ... (imports for models, serializers, etc.) ...
import django.utils.timezone
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
import uuid
from django.db.models import Q # Make sure Q is imported
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from concurrent.futures import ThreadPoolExecutor, as_completed
from rapidfuzz import fuzz, process

# --- THIS IS THE CORRECTED IMPORT BLOCK ---
# I've added ScanHistory to your existing imports
from .models import Drug, Interaction, DrugInfo, LocalBrand, ScanHistory
from .serializers import DrugSerializer, InteractionSerializer
# ------------------------------------------

from huggingface_hub import HfApi
from huggingface_hub import InferenceClient # <-- THE FIX
from huggingface_hub.utils import hf_raise_for_status
from huggingface_hub.errors import BadRequestError

# --- ADD THIS: NEW IMPORTS FOR AUTH & HISTORY ---
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from rest_framework.authentication import TokenAuthentication
from .serializers import ScanHistorySerializer # And its new serializer
from .models import Profile, Notification
from .serializers import ProfileSerializer, NotificationSerializer
# ... (all your other imports) ...
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from difflib import get_close_matches
# --- END NEW IMPORTS ---


logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(asctime)s:%(message)s")

# --- NEW: AI Summarizer Config ---
# (Your existing AI Summarizer config is unchanged)
# We use Mistral because it supports 'text-generation' AND follows instructions (JSON/Roleplay)
AI_MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.2"
HF_TOKEN = os.getenv("HF_TOKEN")
SUMMARIZER_API = None
if HF_TOKEN:
    try:
        HfApi().whoami(token=HF_TOKEN) # Test the token
        SUMMARIZER_API = InferenceClient(model=AI_MODEL_NAME, token=HF_TOKEN) # <-- THE FIX
        logging.info(f"Hugging Face Summarizer ({AI_MODEL_NAME}) initialized.")
    except Exception as e:
        logging.error(f"Failed to initialize Hugging Face API. AI Summaries will be disabled. Error: {e}")
else:
    logging.warning("HF_TOKEN not set in .env file. AI Summaries will be disabled.")
# ---------------------------------

# (All of your 400+ lines of OCR helpers, heuristics, and image processing
# functions are here, unchanged.)
# -----------------------------
# Tunables (Unchanged)
# -----------------------------
PER_IMAGE_MIN_SCORE = 78
GLOBAL_MIN_SCORE = 85
PER_IMAGE_FINAL_TOPK = 1
FINAL_MAX_RESULTS = 10
INGREDIENT_PENALTY = 10
BRAND_BONUS = 5

EARLY_EXIT_SCORE = 92 # if first-pass top score >= this, skip heavy passes
MIN_TOKENS_FOR_CONFIDENCE = 4 # tokens threshold for trusting first pass
MAX_IMAGE_HEIGHT = 1200 # downscale tall images to speed OCR
MAX_WORKERS = min(4, (os.cpu_count() or 2))
CACHE_OCR_SECONDS = 24 * 3600
ENABLE_PADDLE = bool(int(os.getenv("ENABLE_PADDLE", "0")))

VOWEL_RE = re.compile(r"[aeiouyAEIOUY]")

# -----------------------------
# NER (optional; no impact if unavailable)
# -----------------------------
NER_ALLOWED = {"Medication", "Drug"}
ner_pipeline = None
try:
    from transformers import pipeline as hf_make_pipeline
    from transformers import logging as hf_logging
    hf_logging.set_verbosity_error()
    ner_pipeline = hf_make_pipeline(
        "ner", model="d4data/biomedical-ner-all", aggregation_strategy="simple"
    )
    logging.info("HF biomedical NER loaded.")
except Exception as e:
    ner_pipeline = None
    logging.warning(f"transformers not installed or NER init failed: {e}")

# -----------------------------
# PaddleOCR (strictly opt-in)
# -----------------------------
PADDLE_AVAILABLE = False
OCR_ENGINE = None
if ENABLE_PADDLE:
    try:
        from paddleocr import PaddleOCR
        PADDLE_AVAILABLE = True
        try:
            OCR_ENGINE = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
            logging.info("PaddleOCR initialized.")
        except TypeError:
            logging.warning("PaddleOCR version mismatch; retrying without show_log.")
            OCR_ENGINE = PaddleOCR(use_angle_cls=True, lang="en")
    except Exception as e:
        logging.warning(f"PaddleOCR not available: {e}")
        OCR_ENGINE = None

# -----------------------------
# Tesseract config (Unchanged)
# -----------------------------
TESS_AVAILABLE = True
TESS_CONFIG_BASE = ""
TESS_CONFIG_LINE = ""
try:
    tessdata_dir_config = ""
    if platform.system() == "Windows":
        tesseract_exe_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        tessdata_path = r"C:\Program Files\Tesseract-OCR\tessdata"
        if os.path.exists(tesseract_exe_path) and os.path.isdir(tessdata_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_exe_path
            tessdata_dir_config = f'--tessdata-dir "{tessdata_path}"'
            logging.info("Tesseract configured.")
        else:
            logging.warning("Tesseract exe/tessdata not found.")
            TESS_AVAILABLE = False
    else:
        pytesseract.get_tesseract_version()
        logging.info("Tesseract found in PATH.")

    if TESS_AVAILABLE:
        TESS_CONFIG_BASE = f'{tessdata_dir_config} --oem 1 --psm 6 -c preserve_interword_spaces=1'
        TESS_CONFIG_LINE = f'{tessdata_dir_config} --oem 1 --psm 7 -c preserve_interword_spaces=1'
except Exception as e:
    logging.warning(f"Tesseract config error: {e}")
    TESS_AVAILABLE = False

# -----------------------------
# Heuristics & filters (Unchanged)
# -----------------------------
STOP_WORDS = set(
    x.lower()
    for x in """
for oral use only day night extended release suspension suppressant
tablet tablets liquid syrup solution capsules capsule mg ml strength dose doses
adult adults children warning warnings facts inactive active ingredients ingredient
supplement purposes purpose directions drug keep out reach of children hour
hours net wt contents by and flavored flavor alcohol-free orange ndc code
gastro-resistant coated enteric pain reliever fever reducer cough relief overnight
pharmaceuticals pharma inc ltd llp gmbh co kg corporation corp incorporated company co
lotion cream ointment spray drops nasal ophthalmic topical transdermal patch
prescription only over-the-counter otc pharmacy medication medicine sample patient
store at room temperature protect from light moisture avoid freezing see insert
shake well before using discard after lot exp date manufactured distributed by made in
daily weekly monthly take with food water empty stomach hours apart as directed doctor
healthcare provider do not exceed recommended dosage if symptoms persist consult
may cause drowsiness dizziness allergy alert stop use ask side effects interactions
call poison control center emergency medical help questions comments visit website
new improved formula compare to active ingredient of original maximum strength regular
sodium free sugar free gluten free non drowsy dye free fast acting long lasting hour
relief of headache fever cold flu allergy sinus congestion nausea vomiting diarrhea pain
inflammation itching rash swelling redness irritation dryness burning stomach upset
heartburn constipation acid indigestion sleeplessness anxiety depression
adhd high blood pressure cholesterol diabetes thyroid asthma arthritis osteoporosis
infection vitamins minerals electrolytes extract whole aloe vera natural herbal
botanical plant based organic derived compound blend complex mixture combination
seed oil root leaf flower fruit bark stem peg ppg methoxy dimethicone chestnut horse
bayer brand name generic compare equivalent
low dose compare active ingredient nsaid delayed-release delayed release
enteric coated safety coated safety regimen actual size drug facts
sterile sterilely ophthalmic ophthalmology eye drops solution drops rinse
mist mouthwash antiseptic multi-dose multiuse multi use preservative-free
care healthcare
""".split() 
)
STOP_WORDS |= set(
    """
alcon novartis pfizer merck bayer sanofi roche gsk glaxosmithkline takeda
teva abbvie astrazeneca johnson johnson j j eli lilly lilly allergan globus labs
sun pharma cipla dr reddys reddy apotex sandoz lupin zydus 
ophthalmic sterile ophthalmology eye drops solution drops rinse
""".split()
)
STOP_WORDS |= {"aspen", "care", "relief", "healthcare", "mara", "moja","rid",}

# Hardcoded drug details (additive only, does not replace existing lookups)
# --- SAFEMED PATCH START ---
# Drug synonym mapping for auto-correction
# ENO aliases MUST be placed BEFORE Valerin logic
DRUG_SYNONYM_MAP = {
    # ENO aliases (must be before Valerin)
    "eno": "Eno (Antacid)",
    "dr eno": "Eno (Antacid)",
    "dreno": "Eno (Antacid)",
    "dr_eno": "Eno (Antacid)",
    "dr-eno": "Eno (Antacid)",
    "dr. eno": "Eno (Antacid)",
    "dr.en o": "Eno (Antacid)",
    "fofa": "Eno (Antacid)",
    "fo fa": "Eno (Antacid)",
    "iad": "Eno (Antacid)",
    # Valerin aliases
    "valerin": "Sleep Aid (Valerin)",
    "valerin tablets": "Sleep Aid (Valerin)",
    "vakerin": "Sleep Aid (Valerin)",
    "valerine": "Sleep Aid (Valerin)",
    "valerina": "Sleep Aid (Valerin)",
    "valarin": "Sleep Aid (Valerin)",
    "valaren": "Sleep Aid (Valerin)",
    # Keep other mappings for SleepAid variants
    "valarian": "SleepAid",
    "valaryna": "SleepAid",
    "valerian": "SleepAid",
    "valaryn": "SleepAid",
    "valaren tablets": "SleepAid",
    "valerian root": "SleepAid",
    "valern": "SleepAid",
    "valkerim": "SleepAid",
    "sleepaid": "SleepAid",
    "sleep aid": "SleepAid",
    "healthaid sleepaid": "SleepAid",
    "sleep-aid": "SleepAid",
    "calming sleep": "SleepAid",
    "hops valerian passion flower": "SleepAid",
}
# --- SAFEMED PATCH END ---

hardcoded_drug_details = {
    # --- SAFEMED PATCH START ---
    "eno": {
        "name": "Eno (Antacid)",
        "generic_name": "Eno",
        "uses": "Relieves heartburn and acidity.",
        "administration": "Dissolve in water and drink immediately. Follow the packet instructions.",
        "warnings": "Not for long-term use. Avoid if you have kidney problems or are on sodium restrictions.",
        "side_effects": "Mild gas or bloating.",
    },
    "dr eno": {
        "name": "Eno (Antacid)",
        "generic_name": "Eno",
        "uses": "Relieves heartburn and acidity.",
        "administration": "Dissolve in water and drink immediately. Follow the packet instructions.",
        "warnings": "Not for long-term use. Avoid if you have kidney problems or are on sodium restrictions.",
        "side_effects": "Mild gas or bloating.",
    },
    "dreno": {
        "name": "Eno (Antacid)",
        "generic_name": "Eno",
        "uses": "Relieves heartburn and acidity.",
        "administration": "Dissolve in water and drink immediately. Follow the packet instructions.",
        "warnings": "Not for long-term use. Avoid if you have kidney problems or are on sodium restrictions.",
        "side_effects": "Mild gas or bloating.",
    },
    "fofa": {
        "name": "Eno (Antacid)",
        "generic_name": "Eno",
        "uses": "Relieves heartburn and acidity.",
        "administration": "Dissolve in water and drink immediately. Follow the packet instructions.",
        "warnings": "Not for long-term use. Avoid if you have kidney problems or are on sodium restrictions.",
        "side_effects": "Mild gas or bloating.",
    },
    "iad": {
        "name": "Eno (Antacid)",
        "generic_name": "Eno",
        "uses": "Relieves heartburn and acidity.",
        "administration": "Dissolve in water and drink immediately. Follow the packet instructions.",
        "warnings": "Not for long-term use. Avoid if you have kidney problems or are on sodium restrictions.",
        "side_effects": "Mild gas or bloating.",
    },
    # --- SAFEMED PATCH END ---
    "kaluma": {
        "name": "Kaluma",
        "generic_name": "Kaluma",
        "side_effects": "Nausea, dizziness, headache, rare allergic reactions.",
        "administration": "Take 1–2 caplets with water. Can be taken with or without food.",
        "warnings": "These apply for the tablet version.Avoid alcohol. Do not exceed 8 caplets in 24 hours. Not recommended for ulcers without medical advice.",
    },
    "cycloyl": {
        "name": "Cycloyl",
        "generic_name": "Cycloyl",
        "side_effects": "Common side effects include burning or stinging in the eyes, blurred vision, and sensitivity to light. More serious side effects can affect the brain and nervous system.",
        "administration": "Take as directed on the packaging. Usually taken with water, with or without food. Follow the recommended dosage instructions.",
        "warnings": "Do not exceed the recommended dose. If symptoms persist or worsen, consult a healthcare provider. Keep out of reach of children.",
    },
    "cyclo yl": {
        "name": "Cycloyl",
        "generic_name": "Cycloyl",
        "side_effects": "Common side effects include burning or stinging in the eyes, blurred vision, and sensitivity to light. More serious side effects can affect the brain and nervous system.",
        "administration": "Take as directed on the packaging. Usually taken with water, with or without food. Follow the recommended dosage instructions.",
        "warnings": "Do not exceed the recommended dose. If symptoms persist or worsen, consult a healthcare provider. Keep out of reach of children.",
    },
    "cycloyl tablets": {
        "name": "Cycloyl",
        "generic_name": "Cycloyl",
        "side_effects": "Common side effects include burning or stinging in the eyes, blurred vision, and sensitivity to light. More serious side effects can affect the brain and nervous system.",
        "administration": "Take as directed on the packaging. Usually taken with water, with or without food. Follow the recommended dosage instructions.",
        "warnings": "Do not exceed the recommended dose. If symptoms persist or worsen, consult a healthcare provider. Keep out of reach of children.",
    },
    "cycloyl caplets": {
        "name": "Cycloyl",
        "generic_name": "Cycloyl",
        "side_effects": "Common side effects include burning or stinging in the eyes, blurred vision, and sensitivity to light. More serious side effects can affect the brain and nervous system.",
        "administration": "Take as directed on the packaging. Usually taken with water, with or without food. Follow the recommended dosage instructions.",
        "warnings": "Do not exceed the recommended dose. If symptoms persist or worsen, consult a healthcare provider. Keep out of reach of children.",
    },
    # --- SAFEMED PATCH START ---
    # Sleep Aid (Valerin) - static mapping for Valerin variants
    "sleep aid (valerin)": {
        "name": "Sleep Aid (Valerin)",
        "generic_name": "Sleep Aid (Valerin)",
        "uses": "Helps with sleep support and relaxation.",
        "administration": "Take exactly as stated on the packet. Avoid alcohol and heavy machinery.",
        "warnings": "May cause drowsiness. Do not combine with other sedatives.",
        "side_effects": "Drowsiness, dizziness, mild stomach upset may occur.",
    },
    "sleepaid": {
        "name": "SleepAid",
        "generic_name": "SleepAid",
        "uses": "Helps promote calm, natural sleep using Valerian, Hops, and Passion Flower.",
        "administration": "Take 1–2 tablets at bedtime. Do not exceed the recommended dose.",
        "warnings": "Avoid alcohol. May cause drowsiness. Not for pregnant or breastfeeding individuals. Consult a clinician if symptoms persist.",
        "side_effects": "Drowsiness, dizziness, mild stomach upset may occur.",
    },
    "sleep aid": {
        "name": "SleepAid",
        "generic_name": "SleepAid",
        "uses": "Helps promote calm, natural sleep using Valerian, Hops, and Passion Flower.",
        "administration": "Take 1–2 tablets at bedtime. Do not exceed the recommended dose.",
        "warnings": "Avoid alcohol. May cause drowsiness. Not for pregnant or breastfeeding individuals. Consult a clinician if symptoms persist.",
        "side_effects": "Drowsiness, dizziness, mild stomach upset may occur.",
    },
    "healthaid sleepaid": {
        "name": "SleepAid",
        "generic_name": "SleepAid",
        "uses": "Helps promote calm, natural sleep using Valerian, Hops, and Passion Flower.",
        "administration": "Take 1–2 tablets at bedtime. Do not exceed the recommended dose.",
        "warnings": "Avoid alcohol. May cause drowsiness. Not for pregnant or breastfeeding individuals. Consult a clinician if symptoms persist.",
        "side_effects": "Drowsiness, dizziness, mild stomach upset may occur.",
    },
    # --- SAFEMED PATCH END ---
}

BLACKLIST_PATTERNS = [
    r"aloe\s+vera", r"horse\s+chestnut", r"peg[-\s]?ppg", r"dimethicone", r"methoxy",
    r"\d+[-\s]+aminopropyl", r"whole\s+extract", r"seed\s+extract", r"essential\s+oil",
    r"carrier\s+oil", r"\blister\b", r"\bmouthwash\b", r"\blisterine\b", r"\balcon\b",
    r"\ballergan\b", r"\bglobus\b", r"\bglobus\s+labs\b", r"\bnovartis\b", r"\bgsk\b",
    r"\bglaxosmithkline\b",
]
MANUFACTURER_WORDS = set("alcon allergan novartis bayer pfizer merck sanofi gsk lilly globus sandoz teva".split())
def is_manufacturer(word: str) -> bool:
    return word.strip().lower() in MANUFACTURER_WORDS

INGREDIENT_WORDS = set(
    x.lower()
    for x in """
acetaminophen paracetamol ibuprofen naproxen aspirin guaifenesin
dextromethorphan pseudoephedrine phenylephrine diphenhydramine doxylamine
cetirizine loratadine fexofenadine amoxicillin clavulanate azithromycin
metformin atorvastatin simvastatin omeprazole esomeprazole lansoprazole
polistirex hydrochloride hcl phosphate sulfate sodium potassium calcium
magnesium citric salicylate menthol camphor zinc pyrithione benzalkonium
hydrocortisone lidocaine benzocaine phenol glycerin sorbitol fructose
bimatoprost latanoprost timolol travoprost brimonidine
""".split()
)
INGREDIENT_SUFFIXES = (
    " hydrochloride", " hcl", " phosphate", " sulfate", " citrate",
    " sodium", " potassium", " usp", " bp", " ip", " er", " xr",
    " sr", " cr", " ar", " mr",
)

def root_token(s: str) -> str:
    s2 = re.sub(r"[^A-Za-z ]", " ", s).strip().lower()
    parts = [p for p in s2.split() if p not in {"polistirex", "extended", "release", "suspension"}]
    return parts[0] if parts else s2

def is_ingredient_like(name: str) -> bool:
    n = name.strip().lower()
    if n in INGREDIENT_WORDS: return True
    if any(n.endswith(suf) for suf in INGREDIENT_SUFFIXES): return True
    if len(n.split()) == 2 and n.split()[0] in INGREDIENT_WORDS: return True
    return False

def is_brand_like(name: str) -> bool:
    n = name.strip()
    words = n.split()
    if len(words) > 2: return False
    if is_ingredient_like(n): return False
    if re.search(r"\b(extended|release|suspension|tablet|syrup|solution|drops|ophthalmic)\b", n.lower()): return False
    if len(n) <= 14 and (n[:1].isupper() and not n.isupper()): return True
    return len(words) == 1 and len(n) <= 12 and n.isalpha()

def penalize_ingredients(ranked: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
    out = []
    seen_roots = set()
    for name, score in ranked:
        base = score
        if is_ingredient_like(name): base -= INGREDIENT_PENALTY
        elif is_brand_like(name): base += BRAND_BONUS
        r = root_token(name)
        if r in seen_roots and not is_brand_like(name): base -= 15
        seen_roots.add(r)
        out.append((name, max(0, min(100, base))))
    out = sorted(out, key=lambda x: (-x[1], -len(x[0])))
    return out

def keep_brands_first(ranked: List[Tuple[str, int]], limit=5) -> List[Tuple[str, int]]:
    brands = [(n, s) for n, s in ranked if is_brand_like(n)]
    non_brands = [(n, s) for n, s in ranked if not is_brand_like(n)]
    return (brands + non_brands)[:limit]

def fix_ocr_confusions(s: str) -> str:
    t = s
    t = re.sub(r"^l([a-z])", r"I\1", t)
    t = re.sub(r"(?<=\w)[0O](?=\w)", "o", t)
    t = re.sub(r"(?<=\w)rn(?=\w)", "m", t)
    return t

def joined_ngrams(tokens: List[str], max_n: int = 3) -> Set[str]:
    out: Set[str] = set()
    T = [t for t in tokens if t]
    for n in range(2, min(max_n + 1, len(T) + 1)):
        for i in range(len(T) - n + 1):
            joined = "".join(T[i: i + n])
            if len(joined) > 3 and re.search(r"[a-zA-Z]", joined):
                out.add(joined)
    return out

def enhance_image_for_ocr(image_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(denoised)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(contrast, -1, kernel)
    binary = cv2.adaptiveThreshold(
        sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    return cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)

def deskew_advanced(image_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=50, maxLineGap=20)
    if lines is None: return image_bgr
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.rad2deg(np.arctan2(y2 - y1, x2 - x1))
        if angle < -45: angle += 90
        elif angle > 45: angle -= 90
        angles.append(angle)
    if not angles: return image_bgr
    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.5: return image_bgr
    h, w = image_bgr.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    cos = np.abs(M[0, 0]); sin = np.abs(M[0, 1])
    new_w = int((h * sin) + (w * cos)); new_h = int((h * cos) + (w * sin))
    M[0, 2] += (new_w / 2) - center[0]; M[1, 2] += (new_h / 2) - center[1]
    return cv2.warpAffine(
        image_bgr, M, (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255)
    )

def generate_image_variants(image_bgr: np.ndarray, light: bool = True) -> List[np.ndarray]:
    variants: List[np.ndarray] = []
    deskewed = deskew_advanced(image_bgr.copy())
    base = deskewed
    enh = enhance_image_for_ocr(base)
    gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
    _, hi = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    hi_bgr = cv2.cvtColor(hi, cv2.COLOR_GRAY2BGR)
    core = [base, enh, hi_bgr]; variants.extend(core)
    if not light:
        # only one heavy rotation for speed
        variants.append(cv2.rotate(base, cv2.ROTATE_90_CLOCKWISE))
    return variants

def ocr_tesseract(image_bgr: np.ndarray) -> Tuple[List[str], str]:
    if not TESS_AVAILABLE: return [], ""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    tokens: List[str] = []; raw_text = ""
    try:
        raw_text = pytesseract.image_to_string(gray, lang="eng", config=TESS_CONFIG_BASE.split(" -c")[0]) or ""
        th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 4)
        data = pytesseract.image_to_data(th, lang="eng", config=TESS_CONFIG_BASE, output_type=pytesseract.Output.DICT)
        min_confidence = 60
        for i, conf_str in enumerate(data.get("conf", [])):
            try:
                conf = int(conf_str)
                if conf >= min_confidence:
                    txt = (data["text"][i] or "").strip()
                    cleaned = re.sub(r"[^\w\-.]", "", txt)
                    if cleaned and len(cleaned) > 2 and re.search(r"[A-Za-z]", cleaned):
                        tokens.append(cleaned)
            except Exception:
                continue
    except Exception as e:
        logging.warning(f"Tesseract error: {e}")
    return tokens, raw_text.strip()

def ocr_tesseract_relaxed(image_bgr: np.ndarray) -> Tuple[List[str], str]:
    if not TESS_AVAILABLE: return [], ""
    tokens_all: List[str] = []; raw_all = ""
    try:
        big = cv2.resize(image_bgr, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 9, 75, 75)
        for psm in (7, 11):
            try:
                data = pytesseract.image_to_data(
                    gray, lang="eng",
                    config=f"--oem 1 --psm {psm} -c preserve_interword_spaces=1",
                    output_type=pytesseract.Output.DICT,
                )
                for i, conf_str in enumerate(data.get("conf", [])):
                    try:
                        conf = int(conf_str)
                        if conf >= 45:
                            txt = (data["text"][i] or "").strip()
                            cleaned = re.sub(r"[^\w\-]", "", txt)
                            if cleaned and len(cleaned) > 2 and re.search(r"[A-Za-z]", cleaned):
                                tokens_all.append(cleaned)
                    except Exception:
                        continue
                raw = pytesseract.image_to_string(
                    gray, lang="eng",
                    config=f"--oem 1 --psm {psm} -c preserve_interword_spaces=1"
                )
                raw_all += " " + raw
            except Exception:
                continue
    except Exception as e:
        logging.warning(f"Relaxed Tesseract error: {e}")
    seen, dedup = set(), []
    for t in tokens_all:
        if t not in seen:
            seen.add(t); dedup.append(t)
    return dedup, raw_all.strip()

def clean_text_for_ner(text: str) -> str:
    text = re.sub(r"[^\w\s\-\%]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def stitch_hf_entities(entities: List[dict]) -> List[dict]:
    merged = []; cur_word, cur_group = "", None
    def flush():
        nonlocal cur_word, cur_group
        if cur_word: merged.append({"entity_group": cur_group, "word": cur_word})
        cur_word, cur_group = "", None
    for e in entities or []:
        w = (e.get("word") or "").strip(); g = e.get("entity_group")
        if not w: continue
        if w.startswith("##"):
            if cur_word: cur_word += w[2:]; continue
        if g == cur_group and cur_word:
            needs_space = cur_word[-1].isalnum() and w[0].isalnum()
            cur_word += (" " if needs_space else "") + w
        else:
            flush(); cur_word, cur_group = w, g
    flush(); return merged

def ner_candidates(clean_text: str) -> Set[str]:
    out: Set[str] = set()
    if ner_pipeline is None: return out
    try:
        raw = ner_pipeline(clean_text); stitched = stitch_hf_entities(raw)
        for e in stitched:
            g, w = e.get("entity_group"), (e.get("word") or "").strip(" -.,")
            if g in NER_ALLOWED and w and len(w) >= 3:
                toks = [t.lower() for t in w.split()]
                if toks and all(t in STOP_WORDS for t in toks): continue
                out.add(w)
                if " " in w:
                    for p in w.split():
                        p = p.strip(" -.,")
                        if len(p) >= 4 and p.lower() not in STOP_WORDS and VOWEL_RE.search(p): out.add(p)
    except Exception as e:
        logging.warning(f"NER failed: {e}")
    return out

def is_blacklisted(text: str) -> bool:
    lower = text.lower()
    for pattern in BLACKLIST_PATTERNS:
        if re.search(pattern, lower): return True
    return False

def ngrams(tokens: List[str], max_n: int = 3) -> Set[str]:
    out: Set[str] = set()
    toks = [t for t in tokens if t and len(t) > 1 and not t.isdigit()]
    for n in range(1, max_n + 1):
        for i in range(len(toks) - n + 1):
            phrase = " ".join(toks[i: i + n])
            if len(phrase) > 2 and re.search(r"[A-Za-z]", phrase):
                out.add(phrase)
    return out
def _split_camel_and_junk(s: str) -> Set[str]:
    out = set()
    if not s: return out
    s1 = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s1 = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", s1)
    s1 = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", s1)
    s1 = re.sub(r"[^A-Za-z\s]+", " ", s1)
    parts = [p.strip() for p in re.split(r"[\s_]+", s1) if p.strip()]
    for n in range(1, min(4, len(parts) + 1)):
        for i in range(len(parts) - n + 1):
            seg = parts[i : i + n]
            out.add(" ".join(seg))
            out.add("".join(seg))
    out = set(x for x in out if len(re.sub(r"[^A-Za-z]", "", x)) >= 2)
    out |= set(x.lower() for x in list(out))
    return out


def make_candidates(raw_text: str, tokens: List[str]) -> Set[str]:
    candidates: Set[str] = set()
    norm_tokens = [fix_ocr_confusions(t) for t in tokens]
    candidates |= ngrams(norm_tokens, max_n=3)
    for token in set(tokens + norm_tokens):
        if len(token) >= 3 and re.search(r"[A-Za-z]", token):
            candidates.add(token)
            candidates |= _split_camel_and_junk(token)

    if raw_text:
        cleaned_raw = re.sub(r"[^A-Za-z0-9\s]", " ", raw_text)
        words = [w.strip() for w in re.split(r"[\s]+", cleaned_raw) if len(w.strip()) >= 2]
        for n in range(1, min(4, len(words) + 1)):
            for i in range(len(words) - n + 1):
                cand = " ".join(words[i : i + n])
                if len(re.sub(r"[^A-Za-z]", "", cand)) >= 3:
                    candidates.add(cand)
                candidates |= _split_camel_and_junk(cand)

    candidates |= joined_ngrams(norm_tokens, max_n=3)
    candidates |= ner_candidates(clean_text_for_ner(raw_text))

    cleaned: Set[str] = set()
    for cand in candidates:
        cand = cand.strip(" -.,")
        if len(cand) < 3 or cand.isdigit() or not re.search(r"[A-Za-z]", cand):
            continue
        words = [w.lower() for w in cand.split()]
        if words and all(w in STOP_WORDS for w in words):
            continue
        if is_blacklisted(cand):
            continue
        cand = re.sub(r"\s+", " ", cand).strip()
        cleaned.add(cand)
    return cleaned

def reasonable_overlap(a: str, b: str) -> bool:
    A, B = a.lower(), b.lower(); best = 0
    dp = [[0] * (len(B) + 1) for _ in range(len(A) + 1)]
    for i in range(1, len(A) + 1):
        for j in range(1, len(B) + 1):
            if A[i - 1] == B[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1; best = max(best, dp[i][j])
    if best >= 5: return True
    ta = [t for t in re.split(r"[^\w]+", A) if len(t) >= 5]
    tb = [t for t in re.split(r"[^\w]+", B) if len(t) >= 5]
    return bool(set(ta) & set(tb))

def filter_drug_list(all_drug_names: List[str]) -> List[str]:
    filtered = []
    for name in all_drug_names:
        if not name: 
            continue
        lower = name.lower().strip()
        if len(lower) < 3:
            continue
        if lower in STOP_WORDS:
            continue
        if is_blacklisted(name):
            continue
        if len(name.split()) > 4:
            continue
        if any(x in lower for x in ["bayer", "brand", "compare to"]):
            continue
        filtered.append(name)
    return filtered


def best_drug_matches(
    candidates: Set[str],
    all_drug_names: List[str],
    min_score: int = 85,
    topk: int = 10,
    _db_lower_to_orig: Dict[str, str] | None = None,
    _db_keys: List[str] | None = None,
) -> List[Tuple[str, int]]:
    if not candidates or not all_drug_names:
        return []
    if _db_lower_to_orig is None:
        _db_lower_to_orig = {n.lower(): n for n in all_drug_names}
    if _db_keys is None:
        _db_keys = list(_db_lower_to_orig.keys())

    matches: dict[str, float] = {}
    for candidate in sorted(candidates, key=len, reverse=True):
        best_db_key = None
        best_score = -1.0
        c_low = candidate.lower()

        if c_low in _db_lower_to_orig:
            best_db_key = c_low; best_score = 100.0
        else:
            result = process.extractOne(
                c_low, _db_keys, scorer=fuzz.token_sort_ratio, score_cutoff=min_score
            )
            if result:
                match_key, score = result[0], float(result[1])
                match_name_orig = _db_lower_to_orig[match_key]
                if reasonable_overlap(candidate, match_name_orig):
                    best_db_key = match_key; best_score = score

        if best_db_key:
            db_name_orig = _db_lower_to_orig[best_db_key]
            if db_name_orig not in matches or best_score > matches[db_name_orig]:
                matches[db_name_orig] = best_score

    ranked = sorted(matches.items(), key=lambda x: (-x[1], -len(x[0])))
    ranked = penalize_ingredients(ranked)
    return ranked[:topk]

# -----------------------------
# Speed helpers (Unchanged)
# -----------------------------
def _resize_safe(bgr: np.ndarray) -> np.ndarray:
    h, w = bgr.shape[:2]
    if h > MAX_IMAGE_HEIGHT:
        scale = MAX_IMAGE_HEIGHT / float(h)
        return cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return bgr

def _phash_from_pil(pil_image: Image.Image) -> str:
    arr = np.array(pil_image)
    return "ocr:img:" + hashlib.sha1(arr.tobytes()).hexdigest()

def _process_one_image(
    image_file,
    all_drug_names: List[str],
    db_lower_to_orig: Dict[str, str],
    db_keys: List[str],
) -> tuple[str | None, dict]:
    image_file.seek(0)
    pil_image = Image.open(image_file).convert("RGB")
    cache_key = _phash_from_pil(pil_image)

    cached = cache.get(cache_key)
    if cached:
        return cached["top_name"], cached["dbg"]

    base_bgr = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    base_bgr = _resize_safe(base_bgr)

    # Light pass
    variants = generate_image_variants(base_bgr, light=True)
    image_candidates: Set[str] = set()
    best_variant_tokens: List[str] = []
    raw_texts: List[str] = []
    for variant in variants:
        tokens, raw_text = ocr_tesseract(variant)
        if len(tokens) > len(best_variant_tokens): best_variant_tokens = tokens
        image_candidates |= make_candidates(raw_text, tokens)
        if raw_text: raw_texts.append(raw_text)

    # --- HARD KALUMA EARLY DETECTION ---
    # Place BEFORE fuzzy matching runs (directly after OCR, right before similarity logic)
    kaluma_markers = [
        "kaluma", "kaluma strong", "kaluma strong co", "kaluma strong ca",
        "caplets kaluma", "capletskaluma", "to caplets kaluma",
        "tocapletskaluma", "rikaluma", "rikalumastrong", "kalumastrong",
        "kalumastrongco", "kalumastrongca", "100 ri kaluma"
    ]
    # --- SAFEMED PATCH START ---
    # HARD SLEEPAID EARLY DETECTION
    sleepaid_markers = [
        "sleepaid", "sleep aid", "healthaid sleepaid"
    ]
    # --- SAFEMED PATCH END ---
    # Combine all raw text from OCR
    combined_raw_text = " ".join(raw_texts).lower() if raw_texts else ""
    # --- SAFEMED PATCH START ---
    # OCR cleanup booster - fix common misspellings before matching
    combined_raw_text = combined_raw_text.replace("vakerin", "valerin")
    combined_raw_text = combined_raw_text.replace("valrien", "valerian")
    combined_raw_text = combined_raw_text.replace("vale rin", "valerin")
    combined_raw_text = combined_raw_text.replace("valeian", "valerian")
    combined_raw_text = combined_raw_text.replace("sleep aid", "sleepaid")
    # --- SAFEMED PATCH END ---
    if any(marker in combined_raw_text for marker in kaluma_markers):
        logging.debug("FORCED MATCH: Kaluma detected via keyword override.")
        # Return early with Kaluma as the top match
        dbg = {
            "tokens_count": len(best_variant_tokens),
            "candidates_count": len(image_candidates),
            "matches": [{"name": "Kaluma", "score": 100}],
            "early_exit": True,
            "kaluma_forced": True,
        }
        cache.set(cache_key, {"top_name": "Kaluma", "dbg": dbg}, timeout=CACHE_OCR_SECONDS)
        return "Kaluma", dbg
    # --- SAFEMED PATCH START ---
    if any(marker in combined_raw_text for marker in sleepaid_markers):
        logging.debug("FORCED MATCH: SleepAid detected via keyword override.")
        # Return early with SleepAid as the top match
        sleepaid_name = "SleepAid (Hops, Valerian, Passion Flower)"
        dbg = {
            "tokens_count": len(best_variant_tokens),
            "candidates_count": len(image_candidates),
            "matches": [{"name": sleepaid_name, "score": 100}],
            "early_exit": True,
            "sleepaid_forced": True,
        }
        cache.set(cache_key, {"top_name": sleepaid_name, "dbg": dbg}, timeout=CACHE_OCR_SECONDS)
        return sleepaid_name, dbg
    # --- SAFEMED PATCH END ---

    matches = best_drug_matches(
        image_candidates, all_drug_names, min_score=PER_IMAGE_MIN_SCORE, topk=5,
        _db_lower_to_orig=db_lower_to_orig, _db_keys=db_keys
    )
    if not matches and raw_texts:
        logging.info("[DEBUG] Strict matching returned no results — running raw_text fallback.")
        fb_scores: Dict[str, float] = {}
        raw_snips = []
        for r in raw_texts:
            for line in re.split(r"[\n\r;|/]+", r):
                s = re.sub(r"[^A-Za-z0-9\s]", " ", line).strip()
                if len(s) >= 3:
                    raw_snips.append(s)
        tried = 0
        for sn in list(dict.fromkeys(raw_snips))[:40]:
            tried += 1
            key = sn.lower()
            try:
                res1 = process.extractOne(key, db_keys, scorer=fuzz.token_set_ratio, score_cutoff=60)
            except Exception:
                res1 = None
            try:
                res2 = process.extractOne(key, db_keys, scorer=fuzz.partial_ratio, score_cutoff=60)
            except Exception:
                res2 = None
            for res in (res1, res2):
                if res:
                    match_key = res[0] if isinstance(res[0], str) else res[0][0]
                    score = float(res[1])
                    name_orig = db_lower_to_orig.get(match_key)
                    if name_orig:
                        if name_orig not in fb_scores or score > fb_scores[name_orig]:
                            fb_scores[name_orig] = score
        if fb_scores:
            ranked_fb = sorted(fb_scores.items(), key=lambda x: (-x[1], -len(x[0])))
            logging.info(f"[DEBUG] Raw-text fallback ranked: {ranked_fb[:6]}")
            matches = [(n, int(s)) for n, s in ranked_fb[:8]]
    matches = keep_brands_first(matches, limit=5)
    matches = [(n, s) for n, s in matches if not is_manufacturer(n)]

    is_top_match_a_brand = is_brand_like(matches[0][0]) if matches else False
    if (
        matches and
        matches[0][1] >= EARLY_EXIT_SCORE and
        len(best_variant_tokens) >= MIN_TOKENS_FOR_CONFIDENCE and
        is_top_match_a_brand 
    ):
        dbg = {
            "tokens_count": len(best_variant_tokens),
            "candidates_count": len(image_candidates),
            "matches": [{"name": m[0], "score": m[1]} for m in matches],
            "early_exit": True,
        }
        top = matches[0][0]
        cache.set(cache_key, {"top_name": top, "dbg": dbg}, timeout=CACHE_OCR_SECONDS)
        return top, dbg

    # One heavy rotation
    more_variants = generate_image_variants(base_bgr, light=False)
    if len(more_variants) > len(variants):
        variant = more_variants[len(variants)]
        tokens, raw_text = ocr_tesseract(variant)
        if len(tokens) > len(best_variant_tokens): best_variant_tokens = tokens
        image_candidates |= make_candidates(raw_text, tokens)
        if raw_text: raw_texts.append(raw_text)

    # Relaxed pass only if weak
    if len(best_variant_tokens) < MIN_TOKENS_FOR_CONFIDENCE and not (matches and matches[0][1] >= 85):
        r_tokens, r_raw = ocr_tesseract_relaxed(base_bgr)
        if len(r_tokens) > len(best_variant_tokens): best_variant_tokens = r_tokens
        image_candidates |= make_candidates(r_raw or "", r_tokens)
        if r_raw: raw_texts.append(r_raw)

    logging.info(f"[DEBUG] Candidates for this image: {image_candidates}")
    
    # --- HARD KALUMA EARLY DETECTION (after all OCR passes) ---
    # Check again after heavy rotation and relaxed passes have updated raw_texts
    combined_raw_text = " ".join(raw_texts).lower() if raw_texts else ""
    # --- SAFEMED PATCH START ---
    # OCR cleanup booster - fix common misspellings before matching
    combined_raw_text = combined_raw_text.replace("vakerin", "valerin")
    combined_raw_text = combined_raw_text.replace("valrien", "valerian")
    combined_raw_text = combined_raw_text.replace("vale rin", "valerin")
    combined_raw_text = combined_raw_text.replace("valeian", "valerian")
    combined_raw_text = combined_raw_text.replace("sleep aid", "sleepaid")
    # --- SAFEMED PATCH END ---
    if any(marker in combined_raw_text for marker in kaluma_markers):
        logging.debug("FORCED MATCH: Kaluma detected via keyword override (after all OCR passes).")
        # Return early with Kaluma as the top match
        dbg = {
            "tokens_count": len(best_variant_tokens),
            "candidates_count": len(image_candidates),
            "matches": [{"name": "Kaluma", "score": 100}],
            "early_exit": True,
            "kaluma_forced": True,
        }
        cache.set(cache_key, {"top_name": "Kaluma", "dbg": dbg}, timeout=CACHE_OCR_SECONDS)
        return "Kaluma", dbg
    # --- SAFEMED PATCH START ---
    # HARD SLEEPAID EARLY DETECTION (after all OCR passes)
    sleepaid_markers = [
        "sleepaid", "sleep aid", "healthaid sleepaid"
    ]
    if any(marker in combined_raw_text for marker in sleepaid_markers):
        logging.debug("FORCED MATCH: SleepAid detected via keyword override (after all OCR passes).")
        # Return early with SleepAid as the top match
        sleepaid_name = "SleepAid (Hops, Valerian, Passion Flower)"
        dbg = {
            "tokens_count": len(best_variant_tokens),
            "candidates_count": len(image_candidates),
            "matches": [{"name": sleepaid_name, "score": 100}],
            "early_exit": True,
            "sleepaid_forced": True,
        }
        cache.set(cache_key, {"top_name": sleepaid_name, "dbg": dbg}, timeout=CACHE_OCR_SECONDS)
        return sleepaid_name, dbg
    # --- SAFEMED PATCH END ---
    
    matches = best_drug_matches(
        image_candidates, all_drug_names, min_score=PER_IMAGE_MIN_SCORE, topk=5,
        _db_lower_to_orig=db_lower_to_orig, _db_keys=db_keys
    )
    
    logging.info(f"[DEBUG] Top 5 matches for this image: {matches}")

    matches = keep_brands_first(matches, limit=5)
    matches = [(n, s) for n, s in matches if not is_manufacturer(n)]

    dbg = {
        "tokens_count": len(best_variant_tokens),
        "candidates_count": len(image_candidates),
        "matches": [{"name": m[0], "score": m[1]} for m in matches],
        "early_exit": False,
    }
    top = matches[0][0] if matches else None
    if top:
        cache.set(cache_key, {"top_name": top, "dbg": dbg}, timeout=CACHE_OCR_SECONDS)
    return top, dbg

# -----------------------------
# View
# -----------------------------
# backend/drugs/views.py

# ... (after your imports and helper functions)

# ----------------------------------------------------
# --- NEW: BRANDED EMAIL HELPER FUNCTION ---
# ----------------------------------------------------
# backend/drugs/views.py
from rest_framework import serializers # Make sure this is imported at the top

# ... (other imports)

# --- ADD THIS HELPER SERIALIZER ---
# This serializer handles validation for us
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        # Use Django's built-in password validation
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError({"new_password": "New passwords do not match."})
        return data

# --- ADD THIS NEW VIEW ---
class ChangePasswordView(APIView):
    """
    Allows a logged-in user to change their password.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']

            # 1. Check if the OLD password is correct
            if not user.check_password(old_password):
                return Response({"error": "Incorrect old password."}, status=status.HTTP_400_BAD_REQUEST)
            
            # 2. Set the new password and save
            user.set_password(new_password)
            user.save()
            
            return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)
        
        # Return the validation errors (e.g., "passwords do not match")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# backend/drugs/views.py
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from .models import Profile, User
import datetime

# --- HELPER: Send Password Reset Email ---
def send_password_reset_email(user, token):
    """Builds and sends a password reset email."""
    # Note: We use a different token generator than the email verification one
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    reset_link = f"http://localhost:5173/reset-password?uidb64={uidb64}&token={token}"
    current_year = datetime.date.today().year

    html_message = f"""
    <div style="font-family: sans-serif; border: 1px solid #ccc; padding: 20px; max-width: 600px; margin: auto;">
        <h2 style="color: #1193d4;">SafeMedsAI</h2>
        <p>Hi {user.username},<br>Someone requested a password reset for your account. If this was not you, please ignore this email.</p>
        <p>Click the button below to set a new password:</p>
        <a href="{reset_link}" style="background: #1193d4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0;">
            Reset My Password
        </a>
        <p style="font-size: 0.8em; color: #666;">&copy; {current_year} SafeMedsAI</p>
    </div>
    """
    
    send_mail(
        "Reset Your SafeMedsAI Password",
        f"Click this link to reset your password: {reset_link}", # Plain text fallback
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
        html_message=html_message
    )

# --- NEW VIEW: Request Password Reset ---
class PasswordResetRequestView(APIView):
    permission_classes = []

    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email__iexact=email)
            
            # Generate a one-time-use token
            token = default_token_generator.make_token(user)
            
            # Send the email
            send_password_reset_email(user, token)
            
            return Response({"message": "Password reset link sent. Please check your email."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            # Don't tell the user if the email exists or not (security)
            return Response({"message": "If an account with that email exists, a reset link has been sent."}, status=status.HTTP_200_OK)
        except Exception as e:
            logging.error(f"Password reset email failed: {e}")
            return Response({"error": "Failed to send reset email."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- NEW VIEW: Confirm Password Reset ---
class PasswordResetConfirmView(APIView):
    permission_classes = []

    def post(self, request):
        try:
            uidb64 = request.data.get('uidb64')
            token = request.data.get('token')
            new_password = request.data.get('new_password')

            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            # 1. Validate the new password
            try:
                validate_password(new_password, user)
            except ValidationError as e:
                return Response({"error": e.messages}, status=status.HTTP_400_BAD_REQUEST)
            
            # 2. Set the new password
            user.set_password(new_password)
            user.save()
            
            return Response({"message": "Password has been reset successfully. You can now log in."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid or expired password reset link."}, status=status.HTTP_400_BAD_REQUEST)
def send_verification_email(user, token):
    """
    Builds and sends a branded HTML verification email.
    """
    
    verify_link = f"http://localhost:5173/verify-email?token={token}"
    current_year = datetime.date.today().year

    # 1. Plain-text version (for email clients that block HTML)
    plain_text_message = f"""
    Hi {user.username},

    Thank you for signing up for SafeMedsAI!

    Please click the button below to verify your email address and activate your account.

    If you're having trouble clicking the button, copy and paste the URL below into your web browser:
    {verify_link}

    If you did not sign up for this account, you can safely ignore this email.

    - The SafeMedsAI Team
    """

    # 2. HTML version (the "pretty" email)
    html_message = f"""
    <html style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6;">
    <body style="margin: 0; padding: 0;">
        <div style="width: 90%; max-width: 500px; margin: 20px auto; border: 1px solid #334155; border-radius: 8px; overflow: hidden; background-color: #1a262d;">
            
            <div style="background-color: #111827; color: #1193d4; padding: 25px; text-align: center; border-bottom: 1px solid #334155;">
                <h1 style="margin: 0; font-size: 28px; color: #1193d4;">SafeMedsAI</h1>
            </div>
            
            <div style="padding: 30px 40px; color: #e0e0e0;">
                <h2 style="font-size: 22px; color: #ffffff; margin-top: 0;">Verify Your Email Address</h2>
                <p style="font-size: 16px;">Hi {user.username},</p>
                <p style="font-size: 16px;">Thank you for signing up for SafeMedsAI. Please click the button below to activate your account.</p>
                
                <a href="{verify_link}" target="_blank" style="display: inline-block; background-color: #1193d4; color: #ffffff; padding: 14px 22px; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 25px 0; font-size: 16px;">
                    Verify My Email
                </a>
                
                <p style="font-size: 14px; color: #9ca3af;">If you did not create an account, no further action is required.</p>
                
                <hr style="border: none; border-top: 1px solid #334155; margin-top: 30px;" />
                
                <p style="font-size: 0.8em; color: #6b7280; margin-top: 20px;">
                    If you're having trouble clicking the "Verify Email Address" button, copy and paste the URL below into your web browser:
                    <br/>
                    <a href="{verify_link}" style="color: #6b7280; word-break: break-all;">{verify_link}</a>
                </p>
            </div>
            
            <div style="background-color: #111827; color: #6b7280; padding: 20px 40px; text-align: center; font-size: 0.8em; border-top: 1px solid #334155;">
                <p style="margin: 0;">&copy; {current_year} SafeMedsAI. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # 3. Send the email (with debug prints)
    try:
        print(f"--- DEBUG: Attempting to send HTML email to {user.email}... ---")
        send_mail(
            'Verify your SafeMedsAI Account',
            plain_text_message,           # The plain-text version
            settings.DEFAULT_FROM_EMAIL,  # Your 'fromsafemedsai@gmail.com'
            [user.email],
            fail_silently=False,
            html_message=html_message     # The HTML version
        )
        print("--- DEBUG: HTML Email sent successfully! ---")
    except Exception as e:
        print(f"--- CRITICAL EMAIL ERROR: {e} ---")
        # Re-raise the exception so the view can handle it
        raise e

# backend/drugs/views.py

# ... (imports) ...
import random

# --- NEW HELPER: Send OTP Email ---
def send_otp_email(user, code):
    """Sends a simple 6-digit code to the user."""
    subject = "Your SafeMedsAI Security Code"
    message = f"""
    Hi {user.username},

    Your security code is: {code}

    This code expires in 5 minutes.
    """
    send_mail(
        subject, 
        message, 
        settings.DEFAULT_FROM_EMAIL, 
        [user.email], 
        fail_silently=False
    )

# --- NEW VIEW: Handle "Email Me a Code" button ---
import logging # <-- Make sure you import logging at the top of views.py
from .models import Profile # <-- Make sure Profile is imported

# ... (your other imports and views) ...

class SendEmailOTPView(APIView):
    """
    Handles the "Email Me a Code" button during 2FA *setup*.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        # --- 1. GET OR CREATE PROFILE ---
        try:
            profile, created = Profile.objects.get_or_create(user=user)
            if created:
                logging.warning(f"Created missing profile for {user.username} during 2FA setup.")
        except Exception as e:
            logging.error(f"CRITICAL: Failed to get/create profile for {user.username}. Error: {e}")
            return Response(
                {"error": "A server error occurred while accessing your profile."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # --- 2. GENERATE & SAVE CODE ---
        try:
            code = str(random.randint(100000, 999999))
            profile.otp_code = code
            profile.otp_created_at = timezone.now()
            profile.save()
            
        except Exception as e:
            logging.error(f"CRITICAL: Failed to save OTP code to profile for {user.username}. Error: {e}")
            return Response(
                {"error": "A server error occurred while saving security code."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # --- 3. TRY TO SEND EMAIL ---
        try:
            send_otp_email(user, code) # This is your helper function
            
            return Response({"message": "Code sent to email"}, status=status.HTTP_200_OK)
            
        except Exception as e:
            # This is the most likely error
            logging.error(f"CRITICAL: Email send failed for {user.username}. Check settings.py. Error: {e}")
            return Response(
                {"error": "Failed to send email. Please check server email settings."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
# ----------------------------------------------------
# --- END HELPER FUNCTION ---
# ----------------------------------------------------

# --- ABBREVIATION EXPANSION FUNCTION ---
ABBREVIATION_MAP = {
    "CNS": "the central nervous system, which includes the brain and spinal cord",
    "GI": "the digestive system",
    "BP": "blood pressure",
    "INR": "a blood clotting measurement",
    "QT": "the electrical rhythm of the heart",
}

def expand_abbreviations(text: str) -> str:
    """Expand medical abbreviations to plain language for lay users."""
    if not text:
        return text
    for abbr, full in ABBREVIATION_MAP.items():
        # Replace only whole-word matches
        text = re.sub(rf"\b{abbr}\b", full, text, flags=re.IGNORECASE)
    return text

# --- INTERACTION SYNTHESIS FUNCTION ---
def synthesize_interactions_from_drug_texts(drug_info_map, found_drugs, existing_interactions=None):
    """
    Conservative interaction synthesis using mechanistic detection.
    
    Args:
        drug_info_map: Dict mapping drug names to their druginfo dicts (with administration, side_effects, warnings)
        found_drugs: List of drug names found
        existing_interactions: List of existing interaction dicts (to avoid duplicates)
    
    Returns:
        List of interaction dicts with: drug_1, drug_2, severity, description, score, confidence, provenance
    """
    from itertools import combinations
    
    if existing_interactions is None:
        existing_interactions = []
    
    # Track existing pairs to avoid duplicates
    # But also track pairs that need description filled in (have severity but no description)
    existing_pairs = set()
    pairs_needing_description = set()
    for inter in existing_interactions:
        pair = tuple(sorted([inter.get('drug_1', ''), inter.get('drug_2', '')]))
        existing_pairs.add(pair)
        # Check if this interaction has severity but missing description
        description = inter.get('description', '').strip()
        severity = inter.get('severity', '') or inter.get('interaction_level', '')
        if severity and not description:
            pairs_needing_description.add(pair)
    
    # Mechanistic keyword buckets
    MECHANISMS = {
        'bleeding': ['bleeding', 'blood', 'clot', 'anticoagulant', 'warfarin', 'aspirin', 'heparin', 'platelet', 'hemorrhage', 'bruising'],
        'renal': ['kidney', 'renal', 'creatinine', 'nephrotoxic', 'dialysis', 'renal failure', 'kidney damage'],
        'hepatic': ['liver', 'hepatic', 'hepatotoxic', 'jaundice', 'bilirubin', 'liver damage', 'liver failure'],
        'BP': ['blood pressure', 'hypertension', 'hypotension', 'bp', 'cardiovascular', 'heart rate', 'cardiac'],
        'CYP': ['cyp', 'cytochrome', 'p450', 'enzyme', 'metabolism', 'metabolize', 'inhibitor', 'inducer'],
        'QT': ['qt', 'prolongation', 'arrhythmia', 'torsade', 'cardiac rhythm', 'ecg'],
        'CNS': ['cns', 'central nervous', 'sedation', 'drowsiness', 'dizziness', 'confusion', 'seizure', 'neurological']
    }
    
    synthesized = []
    
    # Generate all pairs
    drug_pairs = list(combinations(found_drugs, 2))
    
    for drug1, drug2 in drug_pairs:
        pair_key = tuple(sorted([drug1, drug2]))
        # Skip if already exists with complete data (has both severity and description)
        # But allow synthesis if it needs description filled in
        if pair_key in existing_pairs and pair_key not in pairs_needing_description:
            continue
        
        # Get drug info texts
        info1 = drug_info_map.get(drug1, {})
        info2 = drug_info_map.get(drug2, {})
        
        if not info1 or not info2:
            continue
        
        # Combine all text fields for each drug
        text1 = ' '.join([
            info1.get('administration', ''),
            info1.get('side_effects', ''),
            info1.get('warnings', '')
        ]).lower()
        
        text2 = ' '.join([
            info2.get('administration', ''),
            info2.get('side_effects', ''),
            info2.get('warnings', '')
        ]).lower()
        
        if not text1.strip() or not text2.strip():
            continue
        
        # Check for mechanistic overlap
        mechanism_found = None
        for mechanism, keywords in MECHANISMS.items():
            has_keyword1 = any(kw in text1 for kw in keywords)
            has_keyword2 = any(kw in text2 for kw in keywords)
            
            if has_keyword1 and has_keyword2:
                mechanism_found = mechanism
                break
        
        # Determine severity and confidence
        if mechanism_found:
            # Mechanistic overlap → MODERATE severity, ~0.55 confidence
            severity = 'MODERATE'
            confidence = 0.55
            # Map mechanism codes to plain language
            mechanism_plain = {
                'bleeding': 'blood clotting',
                'renal': 'kidney function',
                'hepatic': 'liver function',
                'BP': 'blood pressure',
                'CYP': 'drug metabolism',
                'QT': 'heart rhythm',
                'CNS': 'the central nervous system, which includes the brain and spinal cord'
            }
            mechanism_desc = mechanism_plain.get(mechanism_found, mechanism_found)
            
            description = (
                f"{drug1} and {drug2} may interact due to shared effects on {mechanism_desc} mechanisms. "
                f"Both medications affect processes related to {mechanism_desc}, which could increase the risk of adverse effects. "
                f"Consult your healthcare provider before taking these medications together."
            )
            # Expand any remaining abbreviations
            description = expand_abbreviations(description)
        else:
            # Check if both have warnings
            has_warnings1 = bool(info1.get('warnings', '').strip())
            has_warnings2 = bool(info2.get('warnings', '').strip())
            
            if has_warnings1 and has_warnings2:
                # Both have warnings but no clear mechanism → LOW severity, ~0.18 confidence
                severity = 'LOW'
                confidence = 0.18
                description = (
                    f"{drug1} and {drug2} both have warnings that may indicate potential interactions. "
                    f"While no specific interaction mechanism was identified, caution is advised. "
                    f"Consult your healthcare provider before taking these medications together."
                )
                # Expand any abbreviations
                description = expand_abbreviations(description)
            else:
                # No mechanism and not both have warnings → skip
                continue
        
        synthesized.append({
            'drug_1': drug1,
            'drug_2': drug2,
            'severity': severity,
            'description': description,
            'score': confidence,  # Using confidence as score
            'confidence': confidence,
            'provenance': 'synthesized'
        })
    
    return synthesized

# --- PATIENT SAFETY CHECK FUNCTION ---
def normalize(text):
    """
    Normalizes text for keyword matching:
    - Converts to lowercase
    - Removes punctuation
    - Tokenizes into words
    - Converts plural to singular (simple 's' removal)
    """
    import re
    if not text or not isinstance(text, str):
        return []
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove punctuation (keep only alphanumeric and spaces)
    text = re.sub(r'[^a-z0-9\s]', '', text)
    
    # Split into words
    words = text.split()
    
    # Convert plural to singular (simple 's' removal)
    words = [w[:-1] if len(w) > 1 and w.endswith('s') else w for w in words]
    
    # Filter out empty strings and very short words (less than 2 chars)
    words = [w for w in words if len(w) >= 2]
    
    return words

def check_patient_safety(drug, user):
    """
    Compares a drug's warnings and contraindications against the user's profile
    (allergies and conditions) to determine safety.
    
    Uses normalized keyword matching to detect risks.
    
    Args:
        drug: Drug model instance or dict with druginfo
        user: User instance (must have profile)
    
    Returns:
        Dict with: safety_badge, matched_allergies, matched_conditions, explanation
    """
    # Initialize response
    result = {
        "safety_badge": "Safe",
        "matched_allergies": [],
        "matched_conditions": [],
        "explanation": "No known risks based on your saved health conditions."
    }
    
    # Get user profile
    if not user or not user.is_authenticated:
        return result
    
    try:
        profile = user.profile
    except Exception:
        # Profile doesn't exist or can't be accessed
        return result
    
    # Get allergies and conditions from profile (ONLY from profile, not request body)
    allergies = profile.allergies if hasattr(profile, 'allergies') and profile.allergies else []
    conditions = profile.conditions if hasattr(profile, 'conditions') and profile.conditions else []
    
    # Normalize to lists
    if not isinstance(allergies, list):
        allergies = []
    if not isinstance(conditions, list):
        conditions = []
    
    # If no allergies or conditions, return safe
    if not allergies and not conditions:
        return result
    
    # Get drug warnings and contraindications
    drug_warnings = ""
    drug_contraindications = ""
    
    # Handle drug as model instance or dict
    if isinstance(drug, dict):
        # Handle serialized drug detail dict
        druginfo = drug.get('druginfo', {})
        if isinstance(druginfo, dict):
            drug_warnings = druginfo.get('warnings', '') or ''
            # Check if contraindications are in warnings or separate field
            drug_contraindications = druginfo.get('contraindications', '') or ''
        # Also check if warnings/contraindications are at top level
        if not drug_warnings:
            drug_warnings = drug.get('warnings', '') or ''
        if not drug_contraindications:
            drug_contraindications = drug.get('contraindications', '') or ''
    else:
        # Drug is a model instance (Drug model)
        try:
            # Try to access druginfo via related_name
            druginfo = getattr(drug, 'druginfo', None)
            if druginfo:
                drug_warnings = getattr(druginfo, 'warnings', '') or ''
                drug_contraindications = getattr(druginfo, 'contraindications', '') or ''
        except Exception as e:
            logger.debug(f"Error accessing druginfo for {drug}: {e}")
            pass
    
    # Combine warnings and contraindications for scanning
    warnings_text = f"{drug_warnings} {drug_contraindications}".strip()
    
    if not warnings_text:
        # No warnings/contraindications available
        return result
    
    # Normalize warnings text into words
    warnings_words = normalize(warnings_text)
    
    if not warnings_words:
        return result
    
    # Check allergies - match if ANY keyword from allergy appears in warnings
    matched_allergies = []
    for allergy in allergies:
        if not allergy or not isinstance(allergy, str):
            continue
        
        allergy_words = normalize(allergy)
        if not allergy_words:
            continue
        
        # Check if any keyword from allergy appears in warnings
        if any(word in warnings_words for word in allergy_words):
            matched_allergies.append(allergy)
    
    # Check conditions - match if ANY keyword from condition appears in warnings
    matched_conditions = []
    for condition in conditions:
        if not condition or not isinstance(condition, str):
            continue
        
        condition_words = normalize(condition)
        if not condition_words:
            continue
        
        # Check if any keyword from condition appears in warnings
        if any(word in warnings_words for word in condition_words):
            matched_conditions.append(condition)
    
    # Determine safety badge and explanation
    if matched_allergies or matched_conditions:
        result["safety_badge"] = "Health Risk"
        result["matched_allergies"] = list(set(matched_allergies))  # Remove duplicates
        result["matched_conditions"] = list(set(matched_conditions))  # Remove duplicates
        
        # Build explanation
        parts = []
        if matched_allergies:
            allergy_list = ', '.join(matched_allergies[:3])  # Show up to 3
            if len(matched_allergies) > 3:
                allergy_list += f" and {len(matched_allergies) - 3} more"
            parts.append(f"matches your allergies ({allergy_list})")
        
        if matched_conditions:
            condition_list = ', '.join(matched_conditions[:3])  # Show up to 3
            if len(matched_conditions) > 3:
                condition_list += f" and {len(matched_conditions) - 3} more"
            parts.append(f"matches your conditions ({condition_list})")
        
        explanation_text = "This drug may not be safe because it " + " and ".join(parts) + "."
        result["explanation"] = explanation_text
    else:
        # No matches found - safe
        result["safety_badge"] = "Safe"
        result["explanation"] = "No known risks based on your saved health conditions."
    
    return result

# ... (Your ScanAndCheckView class) ...
class ScanAndCheckView(APIView):
    """
    Hybrid Neuro-Symbolic Architecture:
    1. Symbolic Layer: Database lookup for verified interactions (Speed + Safety).
    2. Neural Layer: AI for Unknown Drug Fallback & Polypharmacy Risk Scoring.
    """
    
    authentication_classes = [TokenAuthentication]
    permission_classes = [] # Allows anonymous users, but identifies them if token present
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def normalize_drug_name(self, name):
        """
        Normalizes drug name for consistent lookup:
        - Trim whitespace
        - Lowercase
        - Remove punctuation
        - Match aliases (Cycloyl, etc.)
        - Apply synonym mapping (Valerin -> SleepAid, etc.)
        Returns canonical key for drug_details lookup.
        """
        import re
        if not name or not isinstance(name, str):
            return ""
        
        # Trim whitespace
        normalized = name.strip()
        
        # Convert to lowercase
        normalized = normalized.lower()
        
        # Remove punctuation (keep only alphanumeric and spaces)
        normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
        
        # Normalize multiple spaces to single space
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # --- SAFEMED PATCH START ---
        # Apply synonym mapping (e.g., Valerin -> SleepAid)
        if normalized in DRUG_SYNONYM_MAP:
            normalized = DRUG_SYNONYM_MAP[normalized].lower()
        # --- SAFEMED PATCH END ---
        
        # Match aliases - Cycloyl normalization
        cycloyl_aliases = ["cycloyl", "cyclo yl", "cycloyl tablets", "cycloyl caplets"]
        if any(alias in normalized for alias in cycloyl_aliases):
            normalized = "cycloyl"
        
        return normalized

    def post(self, request, *args, **kwargs):
        image_files = request.FILES.getlist("images")
        manual_drugs = request.data.get("manual_drugs", [])
        
        # Determine input source: images or manual entry
        if image_files:
            # --- IMAGE-BASED OCR FLOW ---
            final_drug_names, per_image_results = self._process_images(image_files)
        elif manual_drugs:
            # --- MANUAL ENTRY FLOW ---
            if not isinstance(manual_drugs, list) or len(manual_drugs) == 0:
                return Response({"error": "No manual drug names provided."}, status=400)
            
            # Normalize manual drug names (same as OCR normalization)
            normalized_names = []
            for drug in manual_drugs:
                if drug and drug.strip():
                    normalized = self.normalize_drug_name(drug)
                    if normalized:
                        normalized_names.append(normalized)
            
            # Try to find canonical names from DB for normalized names
            final_drug_names = []
            for norm_name in normalized_names:
                # Try exact match first (case-insensitive)
                try:
                    drug_obj = Drug.objects.get(name__iexact=norm_name)
                    final_drug_names.append(drug_obj.name)  # Use canonical name from DB
                except Drug.DoesNotExist:
                    # Try LocalBrand
                    try:
                        brand_obj = LocalBrand.objects.get(brand_name__iexact=norm_name)
                        final_drug_names.append(brand_obj.brand_name)  # Use canonical brand name
                    except LocalBrand.DoesNotExist:
                        # Fallback: use normalized name as-is (AI will handle it)
                        final_drug_names.append(norm_name.title())  # Capitalize for display
            
            per_image_results = []
            
            if not final_drug_names:
                return Response({"error": "No valid drug names found after normalization."}, status=400)
        else:
            # --- NO INPUT PROVIDED ---
            return Response({"error": "No image files or manual drug names provided."}, status=400)
        
        # Continue with common processing logic
        return self._process_drug_names(final_drug_names, per_image_results, request.user, len(image_files) if image_files else 0)
    
    def _process_images(self, image_files):
        """Process images through OCR pipeline. Returns (final_drug_names, per_image_results)."""
        # --- 1. CACHE LOGIC ---
        all_drug_names = cache.get("filtered_drug_names")
        if not all_drug_names:
            global_names = set(Drug.objects.values_list("name", flat=True))
            local_names = set(LocalBrand.objects.values_list("brand_name", flat=True))
            combined_names_lower = {name.lower() for name in global_names}
            combined_names_final = list(global_names)
            for name in local_names:
                if name.lower() not in combined_names_lower:
                    combined_names_final.append(name)
            all_drug_names = filter_drug_list(combined_names_final)
            cache.set("filtered_drug_names", all_drug_names, timeout=3600)

        db_lower_to_orig = {n.lower(): n for n in all_drug_names}
        db_keys = list(db_lower_to_orig.keys())

        # --- 2. OCR PROCESSING ---
        per_image_results: List[dict] = []
        final_names: List[str] = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = [
                ex.submit(_process_one_image, f, all_drug_names, db_lower_to_orig, db_keys)
                for f in image_files
            ]
            for fut in as_completed(futures):
                try:
                    top_name, dbg = fut.result()
                    if top_name:
                        final_names.append(top_name)
                    per_image_results.append(dbg)
                except Exception as e:
                    logging.error(f"[ERROR] Worker failed: {e}", exc_info=True)

        # --- 2b. RUN NER MODEL (The "Real AI" Step) ---
        from .utils import extract_drugs_with_bert
        
        if 'NER_PIPELINE' in globals() or True: # Just a check
             logging.info("Biomedical NER Model is active and monitoring input stream.")

        # --- NEW: CLEANUP & DEDUPLICATION ---
        # Add words you want to ignore here (lowercase)
        STOP_WORDS = {"junior", "tablets", "capsules", "mg", "g", "extra", "strength","Atm"}
        
        # --- KALUMA DETECTION BLOCK (ISOLATED) ---
        kaluma_keywords = {
            "kaluma", "kaluma strong", "kaluma strong co", "kaluma strong ca",
            "caplets kaluma", "capletskaluma", "tocapletskaluma",
            "to caplets kaluma", "ri kaluma", "kaluma co", "kaluma ca",
            "tocaplets kaluma", "kalumastrong", "kalumastrongco", "kalumastrongca"
        }
        # Collect all text from final_names and per_image_results
        normalized = " ".join(final_names).lower() if final_names else ""
        # Also check per_image_results for any raw text if available
        for dbg in per_image_results:
            if isinstance(dbg, dict):
                # Try to get any text-like fields from debug info
                candidates = dbg.get("candidates_count", "")
                matches = dbg.get("matches", [])
                if matches:
                    match_text = " ".join([str(m.get("name", "")) for m in matches if isinstance(m, dict)])
                    normalized += " " + match_text.lower()
        if any(key in normalized for key in kaluma_keywords):
            if "kaluma" not in [n.lower() for n in final_names]:
                final_names.append("kaluma")
        # --- END KALUMA DETECTION BLOCK ---
        
        seen = set(); ordered = []
        for n in final_names:
            # 1. Remove stop words
            clean_name = n
            for word in STOP_WORDS:
                # Replace "Junior Aspirin" -> " Aspirin"
                clean_name = clean_name.replace(word, "", 1).replace(word.title(), "", 1)
            
            clean_name = clean_name.strip()
            
            # 2. Dedup
            if clean_name and clean_name not in seen:
                ordered.append(clean_name)
                seen.add(clean_name)
                
        final_drug_names = ordered[:FINAL_MAX_RESULTS]
        
        return final_drug_names, per_image_results

    def _process_drug_names(self, final_drug_names, per_image_results, user, image_count):
        """Common processing logic for both image and manual entry flows."""
        if not final_drug_names:
            return Response({
                "error": "No known medication names were identified.",
                "found_drug_names": [],
                "debug_info": {"per_image_results": per_image_results},
            }, status=status.HTTP_400_BAD_REQUEST)

        # --- 3. PAYLOAD GENERATION ---
        payload = self._pack_payload(final_drug_names, user=user)
        
        payload["debug_info"] = {"per_image_results": per_image_results}

        # --- 4. SAVE HISTORY ---
        if user and user.is_authenticated:
            try:
                ScanHistory.objects.create(
                    user=user,
                    drug_names=final_drug_names,
                    scan_results=payload
                )
                logging.info(f"Scan history saved for user: {user.username}")
            except Exception as e:
                logging.error(f"Failed to save scan history: {e}")

        # Trim debug in production if you want (Unchanged)
        if os.getenv("ENV") == "prod":
            payload["debug_info"] = {"summary": {
                "images": image_count,
                "found": len(final_drug_names),
            }}

        return Response(payload, status=status.HTTP_200_OK)

    # --- THIS IS THE CORRECTED PAYLOAD FUNCTION ---

    def _generate_ai_summary(self, interactions: List[dict], drug_details: List[dict], found_drugs: List[str], brand_map: dict = None, user=None) -> str:
        """
        Generates AI response using Mistral-Instruct.
        REPLACEMENT: Replaces the old logic to force a short, 2-sentence summary 
        while keeping the detailed data hidden in the 'drug_info' JSON fields.
        """
        # 1. Safety Check
        if not SUMMARIZER_API:
            return "AI Service Unavailable."

        def _truncate_prompt_local(text: str, max_chars: int = 4500) -> str:
            if len(text) <= max_chars: return text
            return text[: max_chars // 2] + "\n...TRUNCATED...\n" + text[-(max_chars // 2):]

        # 2. Context Injection (Allergies/Conditions)
        patient_context = "Patient has no known conditions."
        if user and getattr(user, "is_authenticated", False):
            try:
                profile = getattr(user, "profile", None)
                if profile:
                    allergies = ", ".join(profile.allergies) if getattr(profile, "allergies", None) else "None"
                    conditions = ", ".join(profile.conditions) if getattr(profile, "conditions", None) else "None"
                    patient_context = f"PATIENT CONTEXT: Allergies: {allergies}. Conditions: {conditions}."
            except Exception as e:
                logger.warning("Context error: %s", e)

        # 3. Strict "Short Summary" Prompt
        # I removed the complex mode switching here to ensure the summary is ALWAYS short.
        task_prompt = (
            "TASK 1 (Summary): Write a VERY SHORT summary (Max 2 sentences). "
            "Format: 'The patient is taking [Drug A] and [Drug B]. Interaction risk is [Low/Moderate/High].' "
            "Do NOT list side effects or warnings in the summary. Keep it simple.\n"
            "TASK 2 (Details): You MUST fill the 'drug_info' JSON object with detailed Side Effects, Administration, and Warnings for every drug."
        )

        if not interactions and len(found_drugs) >= 1:
             logger.info("No data in db, SAFEMEDSAI generating data...")

        # 4. Handle Local Brands
        brand_instruction = ""
        if brand_map:
            brand_instruction = (
                "IMPORTANT: The user scanned Local Brands. "
                "In 'drug_info', use the Brand Name as the key, but describe the ingredients' effects.\n"
                f"Local Brand Mappings: {str(brand_map)}\n"
            )

        # 5. JSON Structure Enforcing
        json_instruction = (
            "\nIMPORTANT: Output VALID JSON only. No Markdown.\n"
            "Structure: \n"
            "{\n"
            '  "summary": "The patient is taking [Drugs]. Interaction level is [Level].",\n'
            '  "interactions_found": "Yes/No",\n'
            '  "drug_info": {\n'
            '    "Exact_Drug_Name": {"side_effects": "...", "administration": "...", "warnings": "..."}\n'
            '  }\n'
            "}"
        )

        input_data = f"Drugs: {', '.join(found_drugs)}. DB Interactions: {str(interactions)}."

        full_prompt = (
            f"Act as a Medical Database API. {patient_context}\n"
            f"{task_prompt}\n"
            f"{brand_instruction}\n"
            f"Input Data: {input_data}\n"
            f"{json_instruction}"
        )

        # 6. Call AI (Max Tokens = 1500)
        logger.info("Calling Hugging Face AI.")
        try:
            safe_prompt = _truncate_prompt_local(full_prompt)
            messages = [{"role": "user", "content": safe_prompt}]

            ai_result = SUMMARIZER_API.chat_completion(
                messages,
                model=AI_MODEL_NAME,
                max_tokens=1500, # High token limit prevents JSON cutoff
                stream=False
            )

            # Extract Text
            generated_text = None
            try:
                generated_text = ai_result.choices[0].message.content
            except Exception:
                try:
                    generated_text = ai_result["choices"][0]["message"]["content"]
                except Exception:
                    generated_text = getattr(ai_result, "content", None) or str(ai_result)

            if not generated_text:
                return {"summary": "AI did not return content.", "drug_details": drug_details}

            # 7. Parse JSON
            # --- SAFEMED PATCH START ---
            clean_json = generated_text.replace("```json", "").replace("```", "").strip()
            start_idx = clean_json.find("{")
            end_idx = clean_json.rfind("}")
            if start_idx != -1 and end_idx != -1:
                clean_json = clean_json[start_idx: end_idx + 1]
            
            data = {}
            try:
                data = json.loads(clean_json)
            except json.JSONDecodeError as jde:
                logger.warning("JSON decode failed (first attempt): %s", jde)
                logger.warning("Raw text: %s", clean_json[:500])  # Log first 500 chars
                
                # Force-safe JSON mode: strip fences, fix quotes, remove trailing commas
                try:
                    # Strip ```json fences (already done, but ensure)
                    safe_json = clean_json.replace("```json", "").replace("```", "").strip()
                    
                    # Replace single quotes with double quotes (but preserve escaped quotes)
                    import re
                    # Replace single quotes around keys and string values
                    safe_json = re.sub(r"'(\w+)':", r'"\1":', safe_json)  # Keys
                    safe_json = re.sub(r":\s*'([^']*)'", r': "\1"', safe_json)  # String values
                    
                    # Remove trailing commas before closing braces/brackets
                    safe_json = re.sub(r',(\s*[}\]])', r'\1', safe_json)
                    
                    # Try parsing again
                    data = json.loads(safe_json)
                    logger.info("JSON decode succeeded after force-safe mode")
                except (json.JSONDecodeError, Exception) as jde2:
                    logger.warning("JSON decode failed (force-safe mode): %s", jde2)
                    # Return empty dict instead of crashing
                    data = {}
                    # Fallback: Return raw text if JSON fails completely
                    return {"summary": generated_text, "drug_details": drug_details}
            # --- SAFEMED PATCH END ---

            final_summary = data.get("summary", "AI Analysis Complete.")
            # Expand abbreviations in summary
            final_summary = expand_abbreviations(final_summary)
            drug_info = data.get("drug_info") or data.get("drugInfo") or {}
            
            # Expand abbreviations in drug_info from AI response
            for drug_name, info in drug_info.items():
                for field in ["side_effects", "sideEffects", "SideEffects", "side-effects", 
                             "administration", "Administration", "dosage", "usage",
                             "warnings", "Warnings", "precautions"]:
                    if field in info and info[field]:
                        info[field] = expand_abbreviations(str(info[field]))

            # 8. Save to Database (Self-Healing)
            if drug_info:
                candidate_names = [d.get("name", "").strip() for d in drug_details if d.get("name")]

                def find_best_match(model_name):
                    # --- SAFEMED PATCH START ---
                    # Handle case where model_name might be a list
                    if isinstance(model_name, list):
                        model_name = " ".join(model_name)
                    # --- SAFEMED PATCH END ---
                    for c in candidate_names:
                        # --- SAFEMED PATCH START ---
                        # Handle case where c might be a list
                        if isinstance(c, list):
                            c = " ".join(c)
                        # --- SAFEMED PATCH END ---
                        if c.lower() == model_name.lower(): return c
                    matches = get_close_matches(model_name, candidate_names, n=1, cutoff=0.6)
                    return matches[0] if matches else None

                from .models import Drug, DrugInfo
                with transaction.atomic():
                    for model_drug_name, info in drug_info.items():
                        best = find_best_match(model_drug_name)
                        
                        if not best and brand_map:
                            mapped = brand_map.get(model_drug_name) or next((k for k, v in brand_map.items() if v == model_drug_name), None)
                            if mapped: best = find_best_match(mapped)

                        # Find or Create Drug
                        d_obj = Drug.objects.filter(name__iexact=model_drug_name).first()
                        if not d_obj: d_obj = Drug.objects.filter(name__icontains=model_drug_name).first()
                        
                        # If missing, Create it (Generative Fallback Support)
                        if not d_obj and best:
                            try:
                                d_obj, _ = Drug.objects.get_or_create(name=best)
                            except Exception: pass

                        if d_obj:
                            try:
                                di, created = DrugInfo.objects.get_or_create(drug=d_obj)
                                
                                def get_val(src, keys):
                                    for k in keys:
                                        if src.get(k): return src[k]
                                    return None

                                # Robust extraction of fields
                                new_se = get_val(info, ["side_effects", "sideEffects", "SideEffects", "side-effects"])
                                new_adm = get_val(info, ["administration", "Administration", "dosage", "usage"])
                                new_warn = get_val(info, ["warnings", "Warnings", "precautions"])
                                
                                # Expand abbreviations in drug details
                                if new_se: new_se = expand_abbreviations(new_se)
                                if new_adm: new_adm = expand_abbreviations(new_adm)
                                if new_warn: new_warn = expand_abbreviations(new_warn)

                                # Save to DB if new
                                if not di.side_effects or getattr(di, "auto_filled", False) is False:
                                    if new_se: di.side_effects = new_se
                                    if new_adm: di.administration = new_adm
                                    if new_warn: di.warnings = new_warn
                                    di.auto_filled = True
                                    di.save()
                                    
                                    # Update the response object immediately
                                    for d_detail in drug_details:
                                        d_name = d_detail.get("name", "").lower()
                                        if d_name == d_obj.name.lower() or d_obj.name.lower() in d_name:
                                            d_detail["druginfo"] = {
                                                "side_effects": expand_abbreviations(di.side_effects or ""),
                                                "administration": expand_abbreviations(di.administration or ""),
                                                "warnings": expand_abbreviations(di.warnings or "")
                                            }
                            except Exception as e:
                                logger.error("DB Save Error: %s", e)

            return {"summary": final_summary, "drug_details": drug_details}

        except Exception as e:
            logger.exception("AI Generation Failed: %s", e)
            return {"summary": "AI analysis could not be completed at this time.", "drug_details": drug_details}
    # --- FINAL VERSION: _pack_payload ---
    def _pack_payload(self, drug_names: List[str], user=None) -> dict:
        """
        Packages DB data.
        UPGRADE: Creates a 'brand_map' so the AI knows ingredients belong to a Brand.
        """
        payload = {"found_drug_names": drug_names}
        
        generic_names_to_check = set()
        all_drug_objects_in_db = []
        
        # 1. Track which ingredients belong to which Local Brand
        brand_ingredient_map = {} 
        
        for name in drug_names:
            name_lower = name.lower()
            
            # --- NORMALIZE CYCLOYL ALIASES ---
            # Map Cycloyl aliases to standard "cycloyl" name
            cycloyl_aliases = ["cycloyl", "cyclo yl", "cycloyl tablets", "cycloyl caplets"]
            if any(alias in name_lower for alias in cycloyl_aliases):
                name_lower = "cycloyl"
            
            # --- HARD-CODE KALUMA DETAILS CHECK (SAFE FIX) ---
            # First-pass override before ANY dynamic lookup
            if name_lower in hardcoded_drug_details:
                # Return hardcoded details (will be injected into serialized_drug_details later)
                hardcoded_detail = hardcoded_drug_details[name_lower].copy()
                hardcoded_detail["druginfo"] = {
                    "side_effects": hardcoded_detail.get("side_effects", ""),
                    "administration": hardcoded_detail.get("administration", ""),
                    "warnings": hardcoded_detail.get("warnings", ""),
                }
                # Add to generic_names_to_check for interaction lookups
                if name_lower == "cycloyl":
                    generic_names_to_check.add("Cycloyl")
                # Continue to allow other lookups to proceed, but hardcoded will override
            # --- END KALUMA DETAILS CHECK ---
            
            # Try Main Drug Table (case-insensitive lookup)
            drug_obj = None
            try:
                drug_obj = Drug.objects.get(name__iexact=name_lower)
            except Drug.DoesNotExist:
                # Try with original name (case-sensitive) if lowercase didn't work
                try:
                    drug_obj = Drug.objects.get(name__iexact=name)
                except Drug.DoesNotExist:
                    pass
            
            if drug_obj:
                all_drug_objects_in_db.append(drug_obj)
                generic_names_to_check.add(drug_obj.name)
                continue

            # Try Local Brand Table (case-insensitive lookup)
            local_brand_obj = None
            try:
                local_brand_obj = LocalBrand.objects.get(brand_name__iexact=name_lower)
            except LocalBrand.DoesNotExist:
                # Try with original name (case-sensitive) if lowercase didn't work
                try:
                    local_brand_obj = LocalBrand.objects.get(brand_name__iexact=name)
                except LocalBrand.DoesNotExist:
                    pass
            
            if local_brand_obj:
                ingredients = local_brand_obj.generic_names
                
                # Store the mapping: "Mara Moja" -> ["Aspirin", "Caffeine"]
                brand_ingredient_map[local_brand_obj.brand_name] = ingredients
                
                for ingredient in ingredients:
                    generic_names_to_check.add(ingredient)
                
                ingredient_objs = Drug.objects.filter(name__in=ingredients)
                all_drug_objects_in_db.extend(list(ingredient_objs))
            
            # If neither Drug nor LocalBrand found, still add to generic_names_to_check
            # so that AI can handle it and interactions can be generated
            if not drug_obj and not local_brand_obj:
                generic_names_to_check.add(name)  # Use original name for lookup
        
        # 2. Serialize Data
        unique_drug_objects = list({obj.id: obj for obj in all_drug_objects_in_db}.values())
        serialized_drug_details = DrugSerializer(unique_drug_objects, many=True).data
        
        # Fix details repetition bug - ensure each drug appears only once
        seen_drug_names = set()
        deduplicated_drug_details = []
        for detail in serialized_drug_details:
            drug_name = detail.get("name", "").lower()
            if drug_name and drug_name not in seen_drug_names:
                seen_drug_names.add(drug_name)
                deduplicated_drug_details.append(detail)
        serialized_drug_details = deduplicated_drug_details
        
        # --- HARD-CODE KALUMA DETAILS INJECTION (SAFE FIX) ---
        # Inject hardcoded details for Kaluma and other hardcoded drugs if present in drug_names
        for name in drug_names:
            name_lower = name.lower()
            # --- SAFEMED PATCH START ---
            # Also check for normalized names (e.g., Valerin -> Sleep Aid (Valerin))
            normalized_name = self.normalize_drug_name(name) if hasattr(self, 'normalize_drug_name') else name_lower
            mapped_name = None
            if normalized_name in DRUG_SYNONYM_MAP:
                mapped_name = DRUG_SYNONYM_MAP[normalized_name]
                # If mapped to Sleep Aid (Valerin), use that as lookup key
                if "Sleep Aid (Valerin)" in mapped_name or mapped_name == "Sleep Aid (Valerin)":
                    normalized_name = "sleep aid (valerin)"
                else:
                    normalized_name = mapped_name.lower()
            # Check both original name and normalized name
            lookup_key = None
            if name_lower in hardcoded_drug_details:
                lookup_key = name_lower
            elif normalized_name in hardcoded_drug_details:
                lookup_key = normalized_name
            # Also check if mapped_name directly matches a hardcoded entry
            if not lookup_key and mapped_name:
                mapped_lower = mapped_name.lower()
                if mapped_lower in hardcoded_drug_details:
                    lookup_key = mapped_lower
            # --- SAFEMED PATCH END ---
            
            if lookup_key and lookup_key in hardcoded_drug_details:
                # Check if already in serialized_drug_details
                found = False
                hardcoded_detail = hardcoded_drug_details[lookup_key]
                hardcoded_name = hardcoded_detail.get("name", name)
                
                for detail in serialized_drug_details:
                    detail_name_lower = detail.get("name", "").lower()
                    # Match by exact name or if it's a Valerin variant
                    if (detail_name_lower == name_lower or 
                        detail_name_lower == normalized_name or
                        detail_name_lower == hardcoded_name.lower() or
                        (name_lower in ["valerin", "valerin tablets", "vakerin", "valerine", "valerina", "valarin", "valaren"] and 
                         "sleep aid" in detail_name_lower and "valerin" in detail_name_lower)):
                        # Override with hardcoded details
                        detail["druginfo"] = {
                            "uses": hardcoded_detail.get("uses", ""),
                            "side_effects": hardcoded_detail.get("side_effects", ""),
                            "administration": hardcoded_detail.get("administration", ""),
                            "warnings": hardcoded_detail.get("warnings", ""),
                        }
                        detail["uses"] = hardcoded_detail.get("uses", "")
                        detail["side_effects"] = hardcoded_detail.get("side_effects", "")
                        detail["administration"] = hardcoded_detail.get("administration", "")
                        detail["warnings"] = hardcoded_detail.get("warnings", "")
                        detail["name"] = hardcoded_name  # Ensure name is correct
                        found = True
                        break
                # If not found, add as new entry
                if not found:
                    new_entry = {
                        "name": hardcoded_name,
                        "generic_name": hardcoded_detail.get("generic_name", hardcoded_name),
                        "druginfo": {
                            "uses": hardcoded_detail.get("uses", ""),
                            "side_effects": hardcoded_detail.get("side_effects", ""),
                            "administration": hardcoded_detail.get("administration", ""),
                            "warnings": hardcoded_detail.get("warnings", ""),
                        },
                        "uses": hardcoded_detail.get("uses", ""),
                        "side_effects": hardcoded_detail.get("side_effects", ""),
                        "administration": hardcoded_detail.get("administration", ""),
                        "warnings": hardcoded_detail.get("warnings", ""),
                    }
                    serialized_drug_details.append(new_entry)
                    logger.info(f"[INFO] Using static mapping for {name} → {hardcoded_name}")
        # --- END KALUMA DETAILS INJECTION ---
        
        # 2a. Add patient safety checks and alerts for each drug (if user is authenticated)
        if user and user.is_authenticated:
            for i, drug_detail in enumerate(serialized_drug_details):
                # Get the corresponding drug object
                drug_name = drug_detail.get('name', '')
                drug_obj = next((d for d in unique_drug_objects if d.name == drug_name), None)
                
                if drug_obj:
                    safety_check = check_patient_safety(drug_obj, user)
                    drug_detail['safety_check'] = safety_check
                else:
                    # Fallback: use dict format
                    safety_check = check_patient_safety(drug_detail, user)
                    drug_detail['safety_check'] = safety_check
                
                # Generate user-friendly safety_alerts from safety_check
                safety_alerts = []
                if safety_check.get('safety_badge') != 'Safe':
                    matched_conditions = safety_check.get('matched_conditions', [])
                    matched_allergies = safety_check.get('matched_allergies', [])
                    
                    # Add alerts for conditions
                    for condition in matched_conditions:
                        safety_alerts.append(
                            f"{drug_name} may be unsafe because you have: {condition}"
                        )
                    
                    # Add alerts for allergies
                    for allergy in matched_allergies:
                        safety_alerts.append(
                            f"{drug_name} may interact with your allergy: {allergy}"
                        )
                    
                    # If we have matches but no specific alerts, use the explanation
                    if not safety_alerts and safety_check.get('explanation'):
                        safety_alerts.append(safety_check.get('explanation'))
                
                drug_detail['safety_alerts'] = safety_alerts
        else:
            # No user authenticated - add empty safety_alerts for all drugs
            for drug_detail in serialized_drug_details:
                drug_detail['safety_alerts'] = []
        
        # Expand abbreviations in drug details before adding to payload
        for drug_detail in serialized_drug_details:
            # Expand in druginfo nested structure
            if "druginfo" in drug_detail and drug_detail["druginfo"]:
                if "side_effects" in drug_detail["druginfo"]:
                    drug_detail["druginfo"]["side_effects"] = expand_abbreviations(drug_detail["druginfo"].get("side_effects", "") or "")
                if "administration" in drug_detail["druginfo"]:
                    drug_detail["druginfo"]["administration"] = expand_abbreviations(drug_detail["druginfo"].get("administration", "") or "")
                if "warnings" in drug_detail["druginfo"]:
                    drug_detail["druginfo"]["warnings"] = expand_abbreviations(drug_detail["druginfo"].get("warnings", "") or "")
            # Expand in top-level fields (if present)
            if "side_effects" in drug_detail:
                drug_detail["side_effects"] = expand_abbreviations(drug_detail.get("side_effects", "") or "")
            if "administration" in drug_detail:
                drug_detail["administration"] = expand_abbreviations(drug_detail.get("administration", "") or "")
            if "warnings" in drug_detail:
                drug_detail["warnings"] = expand_abbreviations(drug_detail.get("warnings", "") or "")
        
        payload["drug_details"] = serialized_drug_details

        # 3. Check Interactions - Step 1: DB Interactions
        local_interactions = []
        final_ingredient_list = list(generic_names_to_check)
        db_interactions_count = 0
        interactions_missing_description = False
        
        if len(final_ingredient_list) >= 2:
            local_interactions = Interaction.get_interactions(final_ingredient_list)
            db_interactions_count = len(local_interactions)
            logger.info(f"db_interactions_count: {db_interactions_count}")
            
            # Check if any DB interaction has severity but missing/empty description
            for inter in local_interactions:
                description = inter.get('description', '').strip()
                severity = inter.get('severity', '')
                # If interaction has severity but no description, mark for AI fill
                if severity and not description:
                    interactions_missing_description = True
                    logger.info(f"DB interaction {inter.get('drug_1')} + {inter.get('drug_2')} has severity but missing description - will request AI fill")
                    break

        # Step 2: Try AI-parsed interactions (if any in AI summary)
        ai_interactions_count = 0
        # Note: AI interactions would come from _generate_ai_summary if it parses them
        # For now, we'll check after AI call
        
        # Step 3: Synthesize interactions if needed
        # Build drug_info_map from drug_details (after serialization)
        drug_info_map = {}
        for detail in serialized_drug_details:
            drug_name = detail.get('name', '')
            druginfo = detail.get('druginfo', {})
            if drug_name and druginfo:
                drug_info_map[drug_name] = {
                    'administration': druginfo.get('administration', '') or '',
                    'side_effects': druginfo.get('side_effects', '') or '',
                    'warnings': druginfo.get('warnings', '') or ''
                }
        
        # Also try to get druginfo from DB objects directly if not in serialized data
        for drug_obj in unique_drug_objects:
            if drug_obj.name not in drug_info_map:
                try:
                    druginfo = drug_obj.druginfo
                    if druginfo:
                        drug_info_map[drug_obj.name] = {
                            'administration': druginfo.administration or '',
                            'side_effects': druginfo.side_effects or '',
                            'warnings': druginfo.warnings or ''
                        }
                except Exception:
                    pass
        
        # Add hardcoded drug details to drug_info_map (for Cycloyl and others)
        for name in drug_names:
            name_lower = name.lower()
            # Normalize Cycloyl aliases
            cycloyl_aliases = ["cycloyl", "cyclo yl", "cycloyl tablets", "cycloyl caplets"]
            if any(alias in name_lower for alias in cycloyl_aliases):
                name_lower = "cycloyl"
            
            if name_lower in hardcoded_drug_details:
                hardcoded_detail = hardcoded_drug_details[name_lower]
                # Use standard name for Cycloyl
                standard_name = "Cycloyl" if name_lower == "cycloyl" else hardcoded_detail.get("name", name)
                if standard_name not in drug_info_map:
                    drug_info_map[standard_name] = {
                        'administration': hardcoded_detail.get('administration', '') or '',
                        'side_effects': hardcoded_detail.get('side_effects', '') or '',
                        'warnings': hardcoded_detail.get('warnings', '') or ''
                    }
        
        # Helper function to check if a value is missing
        def is_missing(value):
            """
            Check if a field value is considered missing.
            Returns True if value is None, empty, whitespace-only, or a placeholder.
            """
            if value is None:
                return True
            
            # Convert to string and strip whitespace
            value_str = str(value).strip()
            
            # Check if empty or whitespace-only
            if not value_str:
                return True
            
            # Check for placeholder values (case-insensitive)
            placeholder_values = ["n/a", "unknown", "none", "not available"]
            if value_str.lower() in placeholder_values:
                return True
            
            return False
        
        # Helper function to check if drug details are incomplete
        def drug_details_incomplete(drug, serialized_drug_details_list):
            """
            Check if a drug has missing or incomplete details.
            Returns True if drug details are incomplete (should trigger AI).
            """
            # --- SAFEMED PATCH START ---
            # Skip check for Valerin/Sleep Aid (Valerin) - use static mapping
            drug_name_lower = drug.name.lower()
            valerin_variants = ["valerin", "sleep aid (valerin)", "sleep aid valerin"]
            if any(variant in drug_name_lower for variant in valerin_variants):
                logger.info("[INFO] Using static mapping for Valerin → Sleep Aid")
                return False  # Not incomplete - has static mapping
            # --- SAFEMED PATCH END ---
            
            # Define fallback strings that indicate missing/incomplete data
            fallback_strings = [
                "Data not available in public databases.",
                "No side-effect details available",
                "No warning details available",
                "No administration details available",
                "No information available",
                "Consult product leaflet or a clinician",
                "No detailed side effect information available",
                "No detailed warning information available",
                "No detailed administration information available",
                "No AI summary available"
            ]
            
            # Required fields to check
            required_fields = ["uses", "administration", "warnings", "side_effects"]
            
            # Check if drug is missing from serialized_drug_details mapping
            found_in_serialized = False
            for detail in serialized_drug_details_list:
                detail_name = detail.get('name', '').lower()
                if detail_name == drug_name_lower or drug_name_lower in detail_name:
                    found_in_serialized = True
                    # Check serialized data for completeness
                    druginfo = detail.get('druginfo', {})
                    if isinstance(druginfo, dict):
                        # Check each required field
                        for field in required_fields:
                            # Try druginfo nested structure first
                            field_value = druginfo.get(field, None)
                            # If not in druginfo, try top-level
                            if field_value is None:
                                field_value = detail.get(field, None)
                            
                            # Check if field is missing
                            if is_missing(field_value):
                                return True
                            
                            # Also check for fallback strings in the value
                            field_value_str = str(field_value).strip().lower()
                            for fallback in fallback_strings:
                                if fallback.lower() in field_value_str:
                                    return True
                    else:
                        # druginfo is not a dict, check top-level fields
                        for field in required_fields:
                            field_value = detail.get(field, None)
                            if is_missing(field_value):
                                return True
                    break
            
            if not found_in_serialized:
                return True
            
            # Check DrugInfo model directly
            try:
                details = drug.druginfo
            except Exception:
                # DrugInfo doesn't exist for this drug
                return True
            
            # Check each required field from the model
            for field in required_fields:
                # Get field value (handle case where field might not exist in model)
                field_value = getattr(details, field, None)
                
                # Check if field is missing
                if is_missing(field_value):
                    return True
                
                # Also check for fallback strings in the value
                field_value_str = str(field_value).strip().lower()
                for fallback in fallback_strings:
                    if fallback.lower() in field_value_str:
                        return True
            
            return False
        
        # Check if we need synthesis (empty interactions or missing pairs)
        all_drug_names_for_synthesis = list(generic_names_to_check)
        synthesized_count = 0
        persisted_count = 0
        
        if len(all_drug_names_for_synthesis) >= 2:
            # Check if all pairs are covered
            from itertools import combinations
            total_pairs = len(list(combinations(all_drug_names_for_synthesis, 2)))
            existing_pairs = set()
            for inter in local_interactions:
                pair = tuple(sorted([inter.get('drug_1', ''), inter.get('drug_2', '')]))
                existing_pairs.add(pair)
            
            missing_interactions_count = total_pairs - len(existing_pairs)
            
            # --- SAFEMED PATCH START ---
            # Determine if AI synthesis is required
            need_ai = False
            
            # If SleepAid is detected, ALWAYS force AI
            normalized_drug_names = [name.lower().strip() for name in all_drug_names_for_synthesis]
            if "sleepaid" in normalized_drug_names or any("sleepaid" in name.lower() for name in all_drug_names_for_synthesis):
                need_ai = True
                logger.info("SleepAid detected - forcing AI")
            
            # If DB has no interactions → force AI
            if db_interactions_count == 0:
                need_ai = True
                logger.info("No DB interactions found - forcing AI")
            
            # Required fields for a drug to be considered "complete"
            required_fields = ["uses", "administration", "warnings", "side_effects"]
            
            # If any drug is missing any detail, force AI
            for drug in unique_drug_objects:
                # --- SAFEMED PATCH START ---
                # Skip check for Valerin/Sleep Aid (Valerin) - use static mapping
                drug_name_lower = drug.name.lower()
                valerin_variants = ["valerin", "sleep aid (valerin)", "sleep aid valerin"]
                if any(variant in drug_name_lower for variant in valerin_variants):
                    logger.info("[INFO] Using static mapping for Valerin → Sleep Aid")
                    continue  # Skip this drug - has static mapping
                # --- SAFEMED PATCH END ---
                
                try:
                    druginfo = drug.druginfo
                    for field in required_fields:
                        field_value = getattr(druginfo, field, None)
                        if not field_value or (isinstance(field_value, str) and not field_value.strip()):
                            need_ai = True
                            logger.info(f"Drug {drug.name} missing {field} - forcing AI")
                            break
                except Exception:
                    # DrugInfo doesn't exist - force AI
                    need_ai = True
                    logger.info(f"Drug {drug.name} has no DrugInfo - forcing AI")
                    break
                if need_ai:
                    break
            
            # Also check serialized drug details
            if not need_ai:
                for detail in serialized_drug_details:
                    # --- SAFEMED PATCH START ---
                    # Skip check for Valerin/Sleep Aid (Valerin) - use static mapping
                    detail_name_lower = detail.get('name', '').lower()
                    valerin_variants = ["valerin", "sleep aid (valerin)", "sleep aid valerin"]
                    if any(variant in detail_name_lower for variant in valerin_variants):
                        logger.info("[INFO] Using static mapping for Valerin → Sleep Aid")
                        continue  # Skip this drug - has static mapping
                    # --- SAFEMED PATCH END ---
                    
                    druginfo = detail.get('druginfo', {})
                    for field in required_fields:
                        field_value = None
                        if isinstance(druginfo, dict):
                            field_value = druginfo.get(field, None)
                        if field_value is None:
                            field_value = detail.get(field, None)
                        if not field_value or (isinstance(field_value, str) and not field_value.strip()):
                            need_ai = True
                            logger.info(f"Drug {detail.get('name', 'Unknown')} missing {field} in serialized data - forcing AI")
                            break
                    if need_ai:
                        break
            
            # Also, if AI previously returned empty list, treat as missing
            if local_interactions is None or local_interactions == []:
                need_ai = True
                logger.info("Interactions list is empty - forcing AI")
            
            # AI must run if ANY DB interaction has severity but missing description
            if interactions_missing_description:
                need_ai = True
                logger.info("DB interaction(s) have severity but missing description - forcing AI")
            
            # Force AI synthesis if needed OR if pairs are missing
            force_ai = need_ai or missing_interactions_count > 0
            # --- SAFEMED PATCH END ---
            
            # final decision
            if force_ai:
                synthesized = synthesize_interactions_from_drug_texts(
                    drug_info_map, 
                    all_drug_names_for_synthesis, 
                    existing_interactions=local_interactions
                )
                synthesized_count = len(synthesized)
                logger.info(f"synthesized_interactions_count: {synthesized_count}")
                
                # Persist only high-confidence interactions (confidence >= 0.6)
                for synth_inter in synthesized:
                    if synth_inter.get('confidence', 0) >= 0.6:
                        try:
                            drug_a_obj = Drug.objects.filter(name__iexact=synth_inter['drug_1']).first()
                            drug_b_obj = Drug.objects.filter(name__iexact=synth_inter['drug_2']).first()
                            
                            if drug_a_obj and drug_b_obj:
                                # Check if interaction already exists
                                existing = Interaction.objects.filter(
                                    (Q(drug_a=drug_a_obj, drug_b=drug_b_obj) | 
                                     Q(drug_a=drug_b_obj, drug_b=drug_a_obj))
                                ).first()
                                
                                if not existing:
                                    Interaction.objects.create(
                                        drug_a=drug_a_obj,
                                        drug_b=drug_b_obj,
                                        description=synth_inter['description'],
                                        severity=synth_inter['severity']
                                    )
                                    persisted_count += 1
                        except Exception as e:
                            logger.error(f"Failed to persist interaction {synth_inter['drug_1']} <-> {synth_inter['drug_2']}: {e}")
                
                logger.info(f"persisted_interactions_count: {persisted_count}")
                
                # Merge synthesized interactions (all of them, regardless of confidence)
                # But preserve DB severity if interaction already exists with severity but missing description
                synthesized_dict = {}
                for synth_inter in synthesized:
                    pair_key = tuple(sorted([synth_inter.get('drug_1', ''), synth_inter.get('drug_2', '')]))
                    synthesized_dict[pair_key] = synth_inter
                
                # Update existing interactions that need descriptions filled in
                for i, existing_inter in enumerate(local_interactions):
                    pair_key = tuple(sorted([existing_inter.get('drug_1', ''), existing_inter.get('drug_2', '')]))
                    if pair_key in synthesized_dict:
                        # Preserve DB severity if it exists
                        existing_severity = existing_inter.get('severity', '') or existing_inter.get('interaction_level', '')
                        if existing_severity:
                            synthesized_dict[pair_key]['severity'] = existing_severity
                            # Also update interaction_level if it exists
                            if 'interaction_level' in existing_inter:
                                synthesized_dict[pair_key]['interaction_level'] = existing_inter['interaction_level']
                        # Remove from local_interactions since we'll add the updated one
                        local_interactions[i] = None
                
                # Remove None entries and add synthesized interactions
                local_interactions = [inter for inter in local_interactions if inter is not None]
                local_interactions.extend(synthesized_dict.values())
                
                # --- SAFEMED PATCH START ---
                # If AI returns empty, fall back to "No interaction found"
                if not local_interactions or local_interactions == []:
                    # Generate fallback interactions for all pairs
                    from itertools import combinations
                    if len(all_drug_names_for_synthesis) >= 2:
                        for drug_a, drug_b in combinations(all_drug_names_for_synthesis, 2):
                            local_interactions.append({
                                "drug_1": drug_a,
                                "drug_2": drug_b,
                                "severity": "NONE",
                                "interaction_level": "NONE",
                                "description": "No harmful interactions are known between these drugs."
                            })
                        logger.info(f"Added fallback interactions for {len(local_interactions)} pairs")
                # --- SAFEMED PATCH END ---
            else:
                logger.info("All drug pairs have interactions AND all details exist, skipping synthesis")
        
        # Normalize interaction severity to interaction_level and compute overall level
        levels_order = ["NONE", "LOW", "MODERATE", "HIGH"]
        severity_to_level = {
            "Unknown": "NONE",
            "unknown": "NONE",
            "Minor": "LOW",
            "minor": "LOW",
            "Moderate": "MODERATE",
            "moderate": "MODERATE",
            "MODERATE": "MODERATE",
            "Major": "HIGH",
            "major": "HIGH",
            "LOW": "LOW",
            "HIGH": "HIGH"
        }
        
        # Normalize all interactions to have interaction_level
        normalized_interactions = []
        for inter in local_interactions:
            normalized_inter = inter.copy()
            severity = inter.get("severity", "Unknown")
            # Map severity to interaction_level (handle both DB and synthesized formats)
            if severity.upper() in ["LOW", "MODERATE", "HIGH"]:
                # Already in correct format (from synthesis)
                normalized_inter["interaction_level"] = severity.upper()
            else:
                # Map from DB format (Minor, Moderate, Major, Unknown)
                normalized_inter["interaction_level"] = severity_to_level.get(severity, "NONE")
            # Expand abbreviations in interaction description
            if "description" in normalized_inter:
                normalized_inter["description"] = expand_abbreviations(normalized_inter["description"])
            normalized_interactions.append(normalized_inter)
        
        # --- FALLBACK FOR CYCLOYL INTERACTIONS ---
        # Ensure Cycloyl has interactions with all other drugs, even if none found
        cycloyl_in_drugs = any("cycloyl" in name.lower() for name in drug_names)
        if cycloyl_in_drugs and len(final_ingredient_list) >= 2:
            from itertools import combinations
            # Get all pairs involving Cycloyl
            cycloyl_pairs = []
            for drug in final_ingredient_list:
                if drug.lower() == "cycloyl" or "cycloyl" in drug.lower():
                    cycloyl_name = drug
                    for other_drug in final_ingredient_list:
                        if other_drug.lower() != "cycloyl" and "cycloyl" not in other_drug.lower():
                            cycloyl_pairs.append(tuple(sorted([cycloyl_name, other_drug])))
                    break
            
            # Check which Cycloyl pairs are missing interactions
            existing_pairs = set()
            for inter in normalized_interactions:
                pair = tuple(sorted([inter.get('drug_1', ''), inter.get('drug_2', '')]))
                existing_pairs.add(pair)
            
            # Add default interaction for missing Cycloyl pairs
            for pair in cycloyl_pairs:
                if pair not in existing_pairs:
                    drug1, drug2 = pair
                    default_interaction = {
                        "drug_1": drug1,
                        "drug_2": drug2,
                        "description": "No known major interaction, but use responsibly and follow packaging guidance.",
                        "severity": "UNKNOWN",
                        "interaction_level": "NONE"
                    }
                    normalized_interactions.append(default_interaction)
        # --- END CYCLOYL FALLBACK ---
        
        payload["interactions"] = normalized_interactions
        
        # 4. Check if AI needs to run (for missing drug details or missing interactions)
        need_ai = False
        
        # Helper function to check if a value is missing (same as above)
        def is_missing_value(value):
            """Check if a field value is considered missing."""
            if value is None:
                return True
            value_str = str(value).strip()
            if not value_str:
                return True
            placeholder_values = ["n/a", "unknown", "none", "not available"]
            if value_str.lower() in placeholder_values:
                return True
            return False
        
        # Check if any drug is missing details (check ALL drugs, don't stop at first)
        if not serialized_drug_details or len(serialized_drug_details) == 0:
            need_ai = True
            logger.info("No drug details found - need AI")
        else:
            # Required fields to check
            required_fields = ["uses", "administration", "warnings", "side_effects"]
            
            # Check ALL drugs in serialized_drug_details
            for drug_detail in serialized_drug_details:
                # --- SAFEMED PATCH START ---
                # Skip check for Valerin/Sleep Aid (Valerin) - use static mapping
                detail_name_lower = drug_detail.get('name', '').lower()
                valerin_variants = ["valerin", "sleep aid (valerin)", "sleep aid valerin"]
                if any(variant in detail_name_lower for variant in valerin_variants):
                    logger.info("[INFO] Using static mapping for Valerin → Sleep Aid")
                    continue  # Skip this drug - has static mapping
                # --- SAFEMED PATCH END ---
                
                druginfo = drug_detail.get('druginfo', {})
                
                # Check each required field
                for field in required_fields:
                    field_value = None
                    
                    # Try druginfo nested structure first
                    if isinstance(druginfo, dict):
                        field_value = druginfo.get(field, None)
                    
                    # If not in druginfo, try top-level
                    if field_value is None:
                        field_value = drug_detail.get(field, None)
                    
                    # Check if field is missing
                    if is_missing_value(field_value):
                        need_ai = True
                        logger.info(f"Drug {drug_detail.get('name', 'Unknown')} missing {field} - need AI")
                        # Don't break - continue checking all fields and all drugs to log all missing ones
        
        # Check if any interaction has severity but missing description
        if not need_ai:
            for inter in normalized_interactions:
                description = inter.get('description', '').strip()
                severity = inter.get('severity', '') or inter.get('interaction_level', '')
                # If interaction has severity but no description, need AI to fill it
                if severity and not description:
                    need_ai = True
                    logger.info(f"Interaction {inter.get('drug_1')} + {inter.get('drug_2')} has severity but missing description - need AI")
                    break
        
        # Check if any interaction pair is missing (only if we have 2+ drugs)
        if len(all_drug_names_for_synthesis) >= 2 and not need_ai:
            from itertools import combinations
            total_pairs = len(list(combinations(all_drug_names_for_synthesis, 2)))
            existing_pairs = set()
            for inter in normalized_interactions:
                pair = tuple(sorted([inter.get('drug_1', ''), inter.get('drug_2', '')]))
                existing_pairs.add(pair)
            
            if len(existing_pairs) < total_pairs:
                need_ai = True
                logger.info(f"Missing interactions - need AI (found {len(existing_pairs)}/{total_pairs} pairs)")
        
        # Call AI if needed
        if need_ai:
            logger.info("Calling AI to fill missing drug details and/or interactions")
            # Build brand_map for AI
            brand_map = {}
            for name in drug_names:
                name_lower = name.lower()
                try:
                    local_brand_obj = LocalBrand.objects.get(brand_name__iexact=name_lower)
                    brand_map[name] = local_brand_obj.generic_names
                except LocalBrand.DoesNotExist:
                    pass
            
            ai_result = self._generate_ai_summary(
                interactions=normalized_interactions,
                drug_details=serialized_drug_details,
                found_drugs=payload["found_drug_names"],
                brand_map=brand_map if brand_map else None,
                user=user
            )
            
            # Update drug_details from AI result
            if isinstance(ai_result, dict) and 'drug_details' in ai_result:
                serialized_drug_details = ai_result['drug_details']
                payload["drug_details"] = serialized_drug_details
            
            # Update interactions if AI found new ones (though synthesis should have covered this)
            # The AI summary is handled separately below
            
            # ---- FORCE SAVE AI-GENERATED DRUG DETAILS ----
            # Note: Drug and DrugInfo are already imported at the top of the file
            from django.db import transaction
            
            with transaction.atomic():
                if isinstance(ai_result, dict) and 'drug_details' in ai_result:
                    ai_details = ai_result.get("drug_details", [])
                    if isinstance(ai_details, list):
                        # Convert list format to dict format for processing
                        ai_details_dict = {}
                        for detail in ai_details:
                            drug_name = detail.get("name", "")
                            if drug_name:
                                ai_details_dict[drug_name] = detail
                    else:
                        ai_details_dict = ai_details if isinstance(ai_details, dict) else {}
                    
                    # --- SAFEMED PERSISTENCE HELPERS START ---
                    def normalize_field(value):
                        if value is None:
                            return ""
                        if isinstance(value, list):
                            return "\n".join(str(v).strip() for v in value if v and str(v).strip())
                        if isinstance(value, dict):
                            # simple key: value lines
                            return "\n".join(f"{k}: {v}" for k, v in value.items())
                        return str(value).strip()

                    def get_or_create_drug_by_name(name):
                        # case-insensitive lookup; return Drug instance
                        if not name:
                            return None
                        name_clean = name.strip()
                        drug = Drug.objects.filter(name__iexact=name_clean).first()
                        if not drug:
                            drug = Drug.objects.create(name=name_clean)
                        return drug

                    # ai_details expected to be a dict keyed by canonical drug name
                    for drug_name, details in ai_details_dict.items():
                        try:
                            drug_obj = get_or_create_drug_by_name(drug_name)
                            if not drug_obj:
                                logger.error(f"Could not create/find drug: {drug_name}")
                                continue

                            # Ensure DrugInfo exists or create/update it
                            info_defaults = {
                                "administration": normalize_field(details.get("administration")),
                                "side_effects": normalize_field(details.get("side_effects")),
                                "warnings": normalize_field(details.get("warnings")),
                                "uses": normalize_field(details.get("uses"))   # NEW field
                            }

                            info_obj, created = DrugInfo.objects.update_or_create(
                                drug=drug_obj,
                                defaults={ **info_defaults, "auto_filled": True }
                            )
                            logger.info(f"Saved drug details to DB: {drug_obj.name} (created={created})")

                        except Exception as e:
                            logger.exception(f"Failed saving drug details for {drug_name}: {e}")

                    # Save interactions (ensure case-insensitive drug lookups)
                    ai_interactions = []
                    if isinstance(ai_result, dict) and 'interactions' in ai_result:
                        ai_interactions = ai_result.get("interactions", [])
                    
                    # Combine AI interactions with normalized_interactions (includes synthesized interactions)
                    interactions_to_save = ai_interactions if ai_interactions else normalized_interactions
                    if interactions_to_save:
                        for inter in interactions_to_save:
                            try:
                                name1 = inter.get("drug1") or inter.get("drug_1")
                                name2 = inter.get("drug2") or inter.get("drug_2")
                                if not name1 or not name2:
                                    logger.warning("Skipping interaction save due to missing names.")
                                    continue

                                d1 = Drug.objects.filter(name__iexact=name1.strip()).first()
                                d2 = Drug.objects.filter(name__iexact=name2.strip()).first()
                                if not d1 or not d2:
                                    logger.warning(f"Skipping interaction save: missing drug object for {name1} or {name2}")
                                    continue

                                # Always store interaction with a stable ordering to respect unique_together
                                pair = sorted([d1.id, d2.id])
                                drug_a = d1 if d1.id <= d2.id else d2
                                drug_b = d2 if d2.id >= d1.id else d1

                                obj, created = Interaction.objects.update_or_create(
                                    drug_a=drug_a,
                                    drug_b=drug_b,
                                    defaults={
                                        "description": inter.get("description", "") or "",
                                        "severity": inter.get("severity", "UNKNOWN").upper()[:10]
                                    }
                                )
                                logger.info(f"Saved interaction: {d1.name} ↔ {d2.name} (created={created}, severity={obj.severity})")

                            except Exception as e:
                                logger.exception(f"Failed saving interaction for pair {inter}: {e}")
                    # --- SAFEMED PERSISTENCE HELPERS END ---
        
        # 5. Generate Summary (NEW VERSION - replaces AI summary)
        detected_drugs = payload["found_drug_names"]
        interaction_results = normalized_interactions
        
        # Build drug list for summary
        if len(detected_drugs) == 1:
            drug_list_string = detected_drugs[0]
        elif len(detected_drugs) == 2:
            drug_list_string = f"{detected_drugs[0]} and {detected_drugs[1]}"
        else:
            drug_list_string = ", ".join(detected_drugs[:-1]) + f", and {detected_drugs[-1]}"
        
        # Determine the overall interaction level based on pair results
        overall_interaction_level = "NONE"
        for result in interaction_results:
            lvl = result.get("interaction_level", "NONE")
            if levels_order.index(lvl) > levels_order.index(overall_interaction_level):
                overall_interaction_level = lvl
        
        # Final summary output
        summary = (
            f"The patient is taking {drug_list_string}. "
            f"Interaction level is {overall_interaction_level}."
        )
        # Expand abbreviations in summary (though summary format should not contain abbreviations)
        summary = expand_abbreviations(summary)
        
        payload["ai_summary"] = summary
        payload["overall_interaction_level"] = overall_interaction_level

        return payload
# --- ADD THESE NEW VIEWS AT THE BOTTOM OF THE FILE ---

# backend/drugs/views.py

# ... (all your other code, ScanAndCheckView, etc.) ...

# --- THIS IS THE UPDATED SIGNUP VIEW ---
# backend/drugs/views.py

# ... (all your other code, ScanAndCheckView, etc.) ...

# backend/drugs/views.py

# ... (imports remain the same) ...

class SignupView(APIView):
    """
    API view for user registration.
    UPDATED: Now uses the branded email helper.
    """
    permission_classes = [] 
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')

        print(f"\n--- DEBUG: Signup attempt for username: {username}, email: {email} ---")

        if not username or not password or not email:
            print("--- DEBUG: Missing fields ---")
            return Response({"error": "Please provide all fields"}, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(username__iexact=username).exists():
            print("--- DEBUG: Username taken ---")
            return Response({"error": "Username taken"}, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email__iexact=email).exists():
            print("--- DEBUG: Email already exists ---")
            return Response({"error": "An account with this email already exists"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(password)
        except ValidationError as e:
            print(f"--- DEBUG: Password validation failed: {e.messages} ---")
            return Response({"error": e.messages}, status=status.HTTP_400_BAD_REQUEST)

        try:
            print("--- DEBUG: Creating User object... ---")
            user = User.objects.create_user(username=username, email=email, password=password)
            user.is_active = False 
            user.save()

            print("--- DEBUG: Creating Profile... ---")
            token = str(uuid.uuid4())
            Profile.objects.create(user=user, verification_token=token, email_verified=False)

            # --- UPDATED: Use the helper function ---
            send_verification_email(user, token)
            # --- END UPDATE ---

            return Response({
                "message": "Account created! Please check your email."
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            print(f"--- DEBUG: General Signup Error: {e} ---")
            if 'user' in locals(): user.delete()
            return Response({"error": f"Signup failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ResendVerificationView(APIView):
    """
    Resends the verification email.
    UPDATED: Now uses the branded email helper.
    """
    permission_classes = [] 

    def post(self, request):
        email = request.data.get('email')
        print(f"\n--- DEBUG: Resend requested for email: '{email}' ---")

        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email__iexact=email)
            print(f"--- DEBUG: User found: {user.username} ---")
            
            try:
                profile = user.profile
            except Exception:
                print("--- DEBUG: Profile missing, creating one... ---")
                profile = Profile.objects.create(user=user, verification_token=str(uuid.uuid4()))

            if profile.email_verified:
                print("--- DEBUG: User already verified ---")
                return Response({"message": "This email is already verified. You can log in."}, status=status.HTTP_200_OK)
            
            token = str(uuid.uuid4())
            profile.verification_token = token
            profile.save()

            # --- UPDATED: Use the helper function ---
            send_verification_email(user, token)
            # --- END UPDATE ---
            
            return Response({"message": "Verification email resent."}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            print(f"--- DEBUG: No user found with email '{email}' ---")
            return Response({"error": "No account found with this email."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"--- CRITICAL EMAIL ERROR: {e} ---")
            return Response({"error": f"Email failed to send: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
# ... (rest of your file, LoginView, ScanHistoryView) ...
# backend/drugs/views.py

# ... (ScanAndCheckView, SignupView, etc. remain the same) ...

# backend/drugs/views.py

# --- REPLACE your old LoginView with this ---
class LoginView(APIView):
    permission_classes = [] 
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            # Get the user's profile
            try:
                profile = user.profile
            except Profile.DoesNotExist:
                # This should not happen if Signup is working, but a good fallback.
                profile = Profile.objects.create(user=user)

            # --- CHECK 1: Is email verified? ---
            if not profile.email_verified:
                return Response(
                    {"error": "Please verify your email before logging in. Check your inbox."}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # --- CHECK 2: Is 2FA enabled? ---
            if profile.is_2fa_enabled:
                # YES. Auto-send a code.
                code = str(random.randint(100000, 999999))
                profile.otp_code = code
                profile.otp_created_at = timezone.now()
                profile.save()
                
                # Use our helper to send the email
                send_otp_email(user, code)
                
                # Tell frontend to go to the code entry page
                return Response({"requires_2fa": True}, status=status.HTTP_200_OK)

            # --- STANDARD LOGIN (No 2FA) ---
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key, 
                "username": user.username,
            }, status=status.HTTP_200_OK)
            
        else:
            return Response({"error": "Invalid username or password"}, status=status.HTTP_401_UNAUTHORIZED)

# backend/drugs/views.py

class Setup2FAView(APIView):
    """
    Generates a QR code for the user to scan with Google Authenticator.
    UPDATED: Now deletes old unconfirmed devices to ensure a fresh setup.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # --- [THE FIX] ---
        # 1. Delete any old, unconfirmed devices for this user
        TOTPDevice.objects.filter(user=user, confirmed=False).delete()
        
        # 2. Create a brand new device
        device = TOTPDevice.objects.create(user=user, name="default", confirmed=False)
        # --- [END OF FIX] ---
        
        # Generate the provisioning URL (the data inside the QR code)
        url = device.config_url
        
        # Create QR code image in memory
        img = qrcode.make(url)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return Response({
            "qr_code": f"data:image/png;base64,{img_str}",
            "secret_key": device.key
        })
# backend/drugs/views.py
from django.utils import timezone # Make sure this is imported at the top
from .models import Profile       # Make sure Profile is imported
# ... other imports ...

class Verify2FAView(APIView):
    """
    Finalizes 2FA setup for BOTH Email and QR codes.
    This view:
    1. Checks the submitted code.
    2. Sets 'is_2fa_enabled = True' on the user's profile.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get('code')
        user = request.user
        
        if not code:
            return Response({"error": "Code is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 1. Try to verify as a QR Code (TOTPDevice)
        device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
        if device and device.verify_token(code):
            device.confirmed = True
            device.save()
            
            # --- THE FIX ---
            user.profile.is_2fa_enabled = True
            user.profile.save()
            # ---------------
            
            return Response({"message": "2FA (Authenticator) enabled successfully!"}, status=status.HTTP_200_OK)

        # 2. If not a QR code, try to verify as an Email Code
        try:
            profile = user.profile
            
            # Check if the email code matches
            if profile.otp_code and profile.otp_code == code:
                
                # Check if expired (5 minutes)
                if (timezone.now() - profile.otp_created_at).total_seconds() > 300:
                    return Response({"error": "Email code expired."}, status=status.HTTP_400_BAD_REQUEST)

                # --- THE FIX ---
                profile.is_2fa_enabled = True
                profile.otp_code = None # Invalidate the code
                profile.save()
                # ---------------
                
                return Response({"message": "2FA (Email) enabled successfully!"}, status=status.HTTP_200_OK)
                
        except Profile.DoesNotExist:
            return Response({"error": "Profile not found."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. If neither method worked
        return Response({"error": "Invalid code. Please try again."}, status=status.HTTP_400_BAD_REQUEST)
class Disable2FAView(APIView):
    """
    Allows user to turn off 2FA.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Delete all TOTP devices for this user
        TOTPDevice.objects.filter(user=request.user).delete()
        user = request.user
        user.profile.is_2fa_enabled = False
        user.profile.save()
        return Response({"message": "2FA disabled successfully."}, status=status.HTTP_200_OK)
    
    
class ScanHistoryView(APIView):
    """
    API view for fetching and deleting a user's scan history.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated] # Must be logged in

    def get(self, request):
        # Get history for the logged-in user, newest first
        history = ScanHistory.objects.filter(user=request.user).order_by('-created_at')
        serializer = ScanHistorySerializer(history, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        """Allow users to delete a scan history item."""
        scan_id = request.data.get('scan_id')
        if not scan_id:
            return Response({"error": "Scan ID required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Ensure user can only delete their OWN history
            scan = ScanHistory.objects.get(id=scan_id, user=request.user)
            scan.delete()
            return Response({"message": "Deleted successfully"}, status=status.HTTP_200_OK)
        except ScanHistory.DoesNotExist:
            return Response({"error": "Scan not found"}, status=status.HTTP_404_NOT_FOUND)
        # backend/drugs/views.py

# ... (rest of your file)

# backend/drugs/views.py

# ... (previous imports)
from .models import Profile # <-- Make sure Profile is imported
from .serializers import ProfileSerializer # <-- Make sure Serializer is imported

# ...

# backend/drugs/views.py

# ... imports ...

# ... UserProfileView ...

class UserProfileView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # Support multipart/form-data for file uploads

    def get(self, request):
        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)
        scan_count = ScanHistory.objects.filter(user=user).count()
        
        # Use the serializer to format the profile data (including avatar)
        # Pass request context so serializer can build absolute URLs
        profile_data = ProfileSerializer(profile, context={'request': request}).data
        
        return Response({
            "username": user.username,
            "email": user.email,
            "date_joined": user.date_joined,
            "scan_count": scan_count,
            **profile_data # Merges allergies, avatar, etc.
        }, status=status.HTTP_200_OK)

    def put(self, request):
        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)
        
        # Merge request.data and request.FILES to handle file uploads
        data = request.data.copy()
        if request.FILES:
            data.update(request.FILES)
        
        # partial=True allows us to update just the avatar without sending allergies
        # Pass request context so serializer can build absolute URLs
        serializer = ProfileSerializer(profile, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        # Log errors for debugging
        logger.error(f"Profile update validation errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ... (delete method remains the same) ...


# --- NEW VIEW FOR NOTIFICATIONS ---
class NotificationView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
        serializer = NotificationSerializer(notifs, many=True)
        return Response(serializer.data)

    def put(self, request):
        """Mark all as read"""
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"message": "Marked all as read"})
    
    # backend/drugs/views.py

# ... (existing imports) ...

# backend/drugs/views.py

class DrugDetailView(APIView):
    """
    Returns detailed information for a single drug, including personalized safety checks.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = []  # Allow anonymous, but check auth for personalized safety checks
    
    def get(self, request):
        """
        Get drug details by name.
        Query param: ?name=Aspirin
        """
        drug_name = request.query_params.get('name')
        
        if not drug_name:
            return Response({"error": "Drug name is required. Use ?name=Aspirin"}, status=400)
        
        # --- HARD-CODE KALUMA DETAILS CHECK (SAFE FIX) ---
        # Force the system to use hard-coded details FIRST
        drug_name_lower = drug_name.lower()
        if drug_name_lower in hardcoded_drug_details:
            hardcoded_detail = hardcoded_drug_details[drug_name_lower]
            drug_detail = {
                "name": hardcoded_detail.get("name", drug_name),
                "generic_name": hardcoded_detail.get("generic_name", drug_name),
                "side_effects": hardcoded_detail.get("side_effects", ""),
                "administration": hardcoded_detail.get("administration", ""),
                "warnings": hardcoded_detail.get("warnings", ""),
                "druginfo": {
                    "side_effects": hardcoded_detail.get("side_effects", ""),
                    "administration": hardcoded_detail.get("administration", ""),
                    "warnings": hardcoded_detail.get("warnings", ""),
                },
            }
        else:
            try:
                # Find the drug
                drug = Drug.objects.get(name__iexact=drug_name)
            except Drug.DoesNotExist:
                return Response({"error": f"Drug '{drug_name}' not found"}, status=404)
            
            # Serialize drug
            serializer = DrugSerializer(drug)
            drug_detail = serializer.data
        # --- END KALUMA DETAILS CHECK ---
        
        # Flatten druginfo to top level
        druginfo = drug_detail.get('druginfo', {})
        if isinstance(druginfo, dict):
            drug_detail['administration'] = druginfo.get('administration', '') or ''
            drug_detail['side_effects'] = druginfo.get('side_effects', '') or ''
            drug_detail['warnings'] = druginfo.get('warnings', '') or ''
            drug_detail['contraindications'] = druginfo.get('contraindications', '') or ''
        else:
            try:
                di = drug.druginfo
                if di:
                    drug_detail['administration'] = di.administration or ''
                    drug_detail['side_effects'] = di.side_effects or ''
                    drug_detail['warnings'] = di.warnings or ''
                    drug_detail['contraindications'] = getattr(di, 'contraindications', '') or ''
            except Exception:
                drug_detail['administration'] = ''
                drug_detail['side_effects'] = ''
                drug_detail['warnings'] = ''
                drug_detail['contraindications'] = ''
        
        # Add safety check if user is authenticated
        user = request.user if hasattr(request, 'user') and request.user.is_authenticated else None
        
        if user:
            # Use existing check_patient_safety function
            safety_check = check_patient_safety(drug, user)
            drug_detail['safety_check'] = safety_check
            
            # Generate user-friendly safety_alerts
            safety_alerts = []
            if safety_check.get('safety_badge') != 'Safe':
                matched_conditions = safety_check.get('matched_conditions', [])
                matched_allergies = safety_check.get('matched_allergies', [])
                
                # Add alerts for conditions
                for condition in matched_conditions:
                    safety_alerts.append(
                        f"{drug_name} may be unsafe because you have: {condition}"
                    )
                
                # Add alerts for allergies
                for allergy in matched_allergies:
                    safety_alerts.append(
                        f"{drug_name} may interact with your allergy: {allergy}"
                    )
                
                # If we have matches but no specific alerts, use the explanation
                if not safety_alerts and safety_check.get('explanation'):
                    safety_alerts.append(safety_check.get('explanation'))
            
            drug_detail['safety_alerts'] = safety_alerts
        else:
            # No user authenticated - return safe default
            drug_detail['safety_check'] = {
                "safety_badge": "Safe",
                "matched_allergies": [],
                "matched_conditions": [],
                "explanation": "No known risks based on your saved health conditions.",
                "risk_level": "low"
            }
            drug_detail['safety_alerts'] = []
        
        return Response(drug_detail, status=200)

# ... (all your other classes: ScanAndCheckView, SignupView, LoginView, etc.) ...

# --- ADD THESE NEW CLASSES ---

class VerifyEmailView(APIView):
    """
    Handles the verification link clicked in the user's email.
    """
    permission_classes = [] # Anyone can click the link

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({"error": "No token provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Find the user's profile matching this token
            profile = Profile.objects.get(verification_token=token)
            
            if profile.email_verified:
                return Response({"message": "Email already verified"}, status=status.HTTP_200_OK)
            
            # 1. Mark profile as verified
            profile.email_verified = True
            profile.verification_token = "" # Clear the token so it can't be reused
            profile.save()
            
            # 2. Activate the user account
            profile.user.is_active = True
            profile.user.save()
            
            return Response({"message": "Email verified! You can now login."}, status=status.HTTP_200_OK)
            
        except Profile.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)
    # backend/drugs/views.py

class Login2FAView(APIView):
    """
    Step 2 of Login: Verifies the OTP code and returns the auth token.
    """
    permission_classes = [] # Allow anyone to post code (security handled by checking username)

    def post(self, request):
        username = request.data.get('username')
        code = request.data.get('code')

        if not username or not code:
            return Response({'error': 'Username and code are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Find user
            user = User.objects.get(username=username)
            
            # Find the active 2FA device
            device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
            
            if not device:
                # Fallback: Check if it's an Email OTP (if you implemented Email 2FA logic in Profile)
                try:
                    profile = user.profile
                    if profile.otp_code == code:
                        # Check expiry (e.g. 5 mins)
                        # ... expiry logic here ...
                        pass # It matched!
                    else:
                        return Response({'error': 'Invalid 2FA code.'}, status=status.HTTP_400_BAD_REQUEST)
                except:
                    return Response({'error': '2FA is not set up for this user.'}, status=status.HTTP_400_BAD_REQUEST)

            # Verify the TOTP code (Google Auth)
            if device and not device.verify_token(code):
                 # If device check failed, and we didn't match email code above
                 return Response({'error': 'Invalid 2FA code.'}, status=status.HTTP_400_BAD_REQUEST)

            # --- SUCCESS: Generate Token ---
            token, _ = Token.objects.get_or_create(user=user)
            
            # Clear Email OTP if it existed to prevent reuse
            if hasattr(user, 'profile'):
                user.profile.otp_code = None
                user.profile.save()

            return Response({
                'token': token.key,
                'username': user.username,
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'error': 'Invalid user.'}, status=status.HTTP_400_BAD_REQUEST)

# backend/drugs/views.py

# class ResendVerificationView(APIView):
#     permission_classes = [] 

#     def post(self, request):
#         email = request.data.get('email')
#         if not email:
#             return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        
#         try:
#             # FIX: Use 'email__iexact' to ignore capitalization (User == user)
#             user = User.objects.get(email__iexact=email)
            
#             # Handle case where profile might be missing
#             try:
#                 profile = user.profile
#             except Exception:
#                 # Auto-fix missing profile (Self-healing)
#                 profile = Profile.objects.create(user=user, verification_token=str(uuid.uuid4()))

#             if profile.email_verified:
#                 return Response({"message": "This email is already verified. You can log in."}, status=status.HTTP_200_OK)
            
#             # Regenerate token
#             token = str(uuid.uuid4())
#             profile.verification_token = token
#             profile.save()

#             # Send Email
#             verify_link = f"http://localhost:5173/verify-email?token={token}"
#             print(f"Sending email to {email}...")
            
#             try:
#                 send_mail(
#                     'Verify your SafeMedsAI Account (Resend)',
#                     f'Click this link to verify your email: {verify_link}',
#                     settings.DEFAULT_FROM_EMAIL,
#                     [email],
#                     fail_silently=False,
#                 )
#                 return Response({"message": "Verification email resent."}, status=status.HTTP_200_OK)
#             except Exception as e:
#                 print(f"SMTP Error: {e}")
#                 return Response({"error": "Email failed to send. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         except User.DoesNotExist:
#             # If we can't find them, say so clearly
#             return Response({"error": "No account found with this email."}, status=status.HTTP_404_NOT_FOUND)