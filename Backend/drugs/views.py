# backend/drugs/views.py
from __future__ import annotations

import os
import re
import platform
import hashlib
import logging
from itertools import combinations
from typing import List, Set, Tuple, Dict

import numpy as np
import cv2
from PIL import Image
import pytesseract

from django.core.cache import cache
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from concurrent.futures import ThreadPoolExecutor, as_completed
from rapidfuzz import fuzz, process

# --- Your app models/serializers ---
from .models import Drug, Interaction, DrugInfo
from .serializers import DrugSerializer

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(asctime)s:%(message)s")

# -----------------------------
# Tunables
# -----------------------------
PER_IMAGE_MIN_SCORE = 78
GLOBAL_MIN_SCORE    = 85
PER_IMAGE_FINAL_TOPK = 1
FINAL_MAX_RESULTS    = 10
INGREDIENT_PENALTY   = 10
BRAND_BONUS          = 5

EARLY_EXIT_SCORE = 92            # if first-pass top score >= this, skip heavy passes
MIN_TOKENS_FOR_CONFIDENCE = 4    # tokens threshold for trusting first pass
MAX_IMAGE_HEIGHT = 1200          # downscale tall images to speed OCR
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
# Tesseract config
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
# Heuristics & filters
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

def make_candidates(raw_text: str, tokens: List[str]) -> Set[str]:
    candidates: Set[str] = set()
    norm_tokens = [fix_ocr_confusions(t) for t in tokens]
    candidates |= ngrams(norm_tokens, max_n=3)
    for token in set(tokens + norm_tokens):
        if len(token) >= 3 and re.search(r"[A-Za-z]", token):
            candidates.add(token)
    candidates |= joined_ngrams(norm_tokens, max_n=3)
    candidates |= ner_candidates(clean_text_for_ner(raw_text))

    cleaned: Set[str] = set()
    for cand in candidates:
        cand = cand.strip(" -.,")
        if len(cand) < 3 or cand.isdigit() or not re.search(r"[A-Za-z]", cand): continue
        words = [w.lower() for w in cand.split()]
        if words and all(w in STOP_WORDS for w in words): continue
        if is_blacklisted(cand): continue
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
        if is_blacklisted(name): continue
        if len(name.split()) > 4: continue
        lower = name.lower()
        if any(x in lower for x in ["bayer", "brand", "compare to"]): continue
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
# Speed helpers
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

    matches = best_drug_matches(
        image_candidates, all_drug_names, min_score=PER_IMAGE_MIN_SCORE, topk=5,
        _db_lower_to_orig=db_lower_to_orig, _db_keys=db_keys
    )
    matches = keep_brands_first(matches, limit=5)
    matches = [(n, s) for n, s in matches if not is_manufacturer(n)]

    # Early exit
    if matches and matches[0][1] >= EARLY_EXIT_SCORE and len(best_variant_tokens) >= MIN_TOKENS_FOR_CONFIDENCE:
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

    matches = best_drug_matches(
        image_candidates, all_drug_names, min_score=PER_IMAGE_MIN_SCORE, topk=5,
        _db_lower_to_orig=db_lower_to_orig, _db_keys=db_keys
    )
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
class ScanAndCheckView(APIView):
    """
    OCR-based drug/brand extraction (Tesseract-only, brand-first).
    Uses local Interaction DB (DDInter import) for DDI.
    """
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        image_files = request.FILES.getlist("images")
        if not image_files:
            return Response({"error": "No image files provided."}, status=400)

        # Cache and precompute name keys
        all_drug_names = cache.get("filtered_drug_names")
        if not all_drug_names:
            raw_names = list(Drug.objects.values_list("name", flat=True))
            all_drug_names = filter_drug_list(raw_names)
            cache.set("filtered_drug_names", all_drug_names, timeout=3600)

        db_lower_to_orig = {n.lower(): n for n in all_drug_names}
        db_keys = list(db_lower_to_orig.keys())

        logging.info("\n" + "=" * 60)
        logging.info(f"[INFO] Processing {len(image_files)} images")
        logging.info(f"[INFO] Searching against {len(all_drug_names)} pharmaceutical names")
        logging.info("=" * 60 + "\n")

        per_image_results: List[dict] = []
        final_names: List[str] = []

        # Parallel per-image
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
                    return Response({"error": "Server error processing an image."}, status=500)

        # Dedup, cap
        seen = set(); ordered = []
        for n in final_names:
            if n not in seen:
                ordered.append(n); seen.add(n)
        final_drug_names = ordered[:FINAL_MAX_RESULTS]

        logging.info("\n" + "=" * 60)
        if final_drug_names:
            logging.info(f"[RESULT] Identified {len(final_drug_names)} drugs (Unique top picks per image):")
            for n in final_drug_names:
                logging.info(f"  • {n}")
        else:
            logging.info("[RESULT] No drugs identified")
        logging.info("=" * 60 + "\n")

        if not final_drug_names:
            return Response(
                {
                    "error": "No known medication names were identified in the images.",
                    "found_drug_names": [],
                    "debug_info": {"per_image_results": per_image_results},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = self._pack_payload(final_drug_names)
        payload["debug_info"] = {"per_image_results": per_image_results}

        # Trim debug in production if you want
        if os.getenv("ENV") == "prod":
            payload["debug_info"] = {"summary": {
                "images": len(image_files),
                "found": len(final_drug_names),
            }}

        return Response(payload, status=status.HTTP_200_OK)

    def _pack_payload(self, drug_names: List[str]) -> dict:
        """
        Package drug information (from DB) and interactions (from LOCAL DB).
        """
        payload = {"found_drug_names": drug_names}

        # details (Drug + optional DrugInfo via prefetch)
        if drug_names:
            drugs_in_db = Drug.objects.filter(name__in=drug_names).prefetch_related("druginfo")
            payload["drug_details"] = DrugSerializer(drugs_in_db, many=True).data
        else:
            payload["drug_details"] = []

        # local interaction lookup via model helper
        interactions_from_db = []
        if len(drug_names) >= 2:
            logging.info(f"Checking LOCAL DB for interactions among: {drug_names}")
            interactions_from_db = Interaction.get_interactions(drug_names)
        else:
            logging.info("Less than 2 drugs found, skipping interaction check.")

        payload["interactions"] = interactions_from_db
        return payload