# # backend/drugs/views.py
# from __future__ import annotations

# import os
# import re
# import platform
# import hashlib
# import logging
# from itertools import combinations
# from typing import List, Set, Tuple, Dict

# import numpy as np
# import cv2
# from PIL import Image
# import pytesseract

# from django.core.cache import cache
# from rest_framework import status
# from rest_framework.parsers import FormParser, MultiPartParser
# from rest_framework.response import Response
# from rest_framework.views import APIView

# from concurrent.futures import ThreadPoolExecutor, as_completed
# from rapidfuzz import fuzz, process

# # --- Your app models/serializers ---
# # THIS IS CHANGE 1:
# from .models import Drug, Interaction, DrugInfo, LocalBrand
# from .serializers import DrugSerializer, InteractionSerializer

# logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(asctime)s:%(message)s")

# # -----------------------------
# # Tunables
# # -----------------------------
# PER_IMAGE_MIN_SCORE = 78
# GLOBAL_MIN_SCORE    = 85
# PER_IMAGE_FINAL_TOPK = 1
# FINAL_MAX_RESULTS    = 10
# INGREDIENT_PENALTY   = 10
# BRAND_BONUS          = 5

# EARLY_EXIT_SCORE = 92            # if first-pass top score >= this, skip heavy passes
# MIN_TOKENS_FOR_CONFIDENCE = 4    # tokens threshold for trusting first pass
# MAX_IMAGE_HEIGHT = 1200          # downscale tall images to speed OCR
# MAX_WORKERS = min(4, (os.cpu_count() or 2))
# CACHE_OCR_SECONDS = 24 * 3600
# ENABLE_PADDLE = bool(int(os.getenv("ENABLE_PADDLE", "0")))

# VOWEL_RE = re.compile(r"[aeiouyAEIOUY]")

# # -----------------------------
# # NER (optional; no impact if unavailable)
# # -----------------------------
# NER_ALLOWED = {"Medication", "Drug"}
# ner_pipeline = None
# try:
#     from transformers import pipeline as hf_make_pipeline
#     from transformers import logging as hf_logging
#     hf_logging.set_verbosity_error()
#     ner_pipeline = hf_make_pipeline(
#         "ner", model="d4data/biomedical-ner-all", aggregation_strategy="simple"
#     )
#     logging.info("HF biomedical NER loaded.")
# except Exception as e:
#     ner_pipeline = None
#     logging.warning(f"transformers not installed or NER init failed: {e}")

# # -----------------------------
# # PaddleOCR (strictly opt-in)
# # -----------------------------
# PADDLE_AVAILABLE = False
# OCR_ENGINE = None
# if ENABLE_PADDLE:
#     try:
#         from paddleocr import PaddleOCR
#         PADDLE_AVAILABLE = True
#         try:
#             OCR_ENGINE = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
#             logging.info("PaddleOCR initialized.")
#         except TypeError:
#             logging.warning("PaddleOCR version mismatch; retrying without show_log.")
#             OCR_ENGINE = PaddleOCR(use_angle_cls=True, lang="en")
#     except Exception as e:
#         logging.warning(f"PaddleOCR not available: {e}")
#         OCR_ENGINE = None

# # -----------------------------
# # Tesseract config
# # -----------------------------
# TESS_AVAILABLE = True
# TESS_CONFIG_BASE = ""
# TESS_CONFIG_LINE = ""
# try:
#     tessdata_dir_config = ""
#     if platform.system() == "Windows":
#         tesseract_exe_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
#         tessdata_path = r"C:\Program Files\Tesseract-OCR\tessdata"
#         if os.path.exists(tesseract_exe_path) and os.path.isdir(tessdata_path):
#             pytesseract.pytesseract.tesseract_cmd = tesseract_exe_path
#             tessdata_dir_config = f'--tessdata-dir "{tessdata_path}"'
#             logging.info("Tesseract configured.")
#         else:
#             logging.warning("Tesseract exe/tessdata not found.")
#             TESS_AVAILABLE = False
#     else:
#         pytesseract.get_tesseract_version()
#         logging.info("Tesseract found in PATH.")

#     if TESS_AVAILABLE:
#         TESS_CONFIG_BASE = f'{tessdata_dir_config} --oem 1 --psm 6 -c preserve_interword_spaces=1'
#         TESS_CONFIG_LINE = f'{tessdata_dir_config} --oem 1 --psm 7 -c preserve_interword_spaces=1'
# except Exception as e:
#     logging.warning(f"Tesseract config error: {e}")
#     TESS_AVAILABLE = False

# # -----------------------------
# # Heuristics & filters
# # -----------------------------
# STOP_WORDS = set(
#     x.lower()
#     for x in """
# for oral use only day night extended release suspension suppressant
# tablet tablets liquid syrup solution capsules capsule mg ml strength dose doses
# adult adults children warning warnings facts inactive active ingredients ingredient
# supplement purposes purpose directions drug keep out reach of children hour
# hours net wt contents by and flavored flavor alcohol-free orange ndc code
# gastro-resistant coated enteric pain reliever fever reducer cough relief overnight
# pharmaceuticals pharma inc ltd llp gmbh co kg corporation corp incorporated company co
# lotion cream ointment spray drops nasal ophthalmic topical transdermal patch
# prescription only over-the-counter otc pharmacy medication medicine sample patient
# store at room temperature protect from light moisture avoid freezing see insert
# shake well before using discard after lot exp date manufactured distributed by made in
# daily weekly monthly take with food water empty stomach hours apart as directed doctor
# healthcare provider do not exceed recommended dosage if symptoms persist consult
# may cause drowsiness dizziness allergy alert stop use ask side effects interactions
# call poison control center emergency medical help questions comments visit website
# new improved formula compare to active ingredient of original maximum strength regular
# sodium free sugar free gluten free non drowsy dye free fast acting long lasting hour
# relief of headache fever cold flu allergy sinus congestion nausea vomiting diarrhea pain
# inflammation itching rash swelling redness irritation dryness burning stomach upset
# heartburn constipation acid indigestion sleeplessness anxiety depression
# adhd high blood pressure cholesterol diabetes thyroid asthma arthritis osteoporosis
# infection vitamins minerals electrolytes extract whole aloe vera natural herbal
# botanical plant based organic derived compound blend complex mixture combination
# seed oil root leaf flower fruit bark stem peg ppg methoxy dimethicone chestnut horse
# bayer brand name generic compare equivalent
# low dose compare active ingredient nsaid delayed-release delayed release
# enteric coated safety coated safety regimen actual size drug facts
# sterile sterilely ophthalmic ophthalmology eye drops solution drops rinse
# mist mouthwash antiseptic multi-dose multiuse multi use preservative-free
# """.split()
# )
# STOP_WORDS |= set(
#     """
# alcon novartis pfizer merck bayer sanofi roche gsk glaxosmithkline takeda
# teva abbvie astrazeneca johnson johnson j j eli lilly lilly allergan globus labs
# sun pharma cipla dr reddys reddy apotex sandoz lupin zydus
# ophthalmic sterile ophthalmology eye drops solution drops rinse
# """.split()
# )
# BLACKLIST_PATTERNS = [
#     r"aloe\s+vera", r"horse\s+chestnut", r"peg[-\s]?ppg", r"dimethicone", r"methoxy",
#     r"\d+[-\s]+aminopropyl", r"whole\s+extract", r"seed\s+extract", r"essential\s+oil",
#     r"carrier\s+oil", r"\blister\b", r"\bmouthwash\b", r"\blisterine\b", r"\balcon\b",
#     r"\ballergan\b", r"\bglobus\b", r"\bglobus\s+labs\b", r"\bnovartis\b", r"\bgsk\b",
#     r"\bglaxosmithkline\b",
# ]
# MANUFACTURER_WORDS = set("alcon allergan novartis bayer pfizer merck sanofi gsk lilly globus sandoz teva".split())
# def is_manufacturer(word: str) -> bool:
#     return word.strip().lower() in MANUFACTURER_WORDS

# INGREDIENT_WORDS = set(
#     x.lower()
#     for x in """
# acetaminophen paracetamol ibuprofen naproxen aspirin guaifenesin
# dextromethorphan pseudoephedrine phenylephrine diphenhydramine doxylamine
# cetirizine loratadine fexofenadine amoxicillin clavulanate azithromycin
# metformin atorvastatin simvastatin omeprazole esomeprazole lansoprazole
# polistirex hydrochloride hcl phosphate sulfate sodium potassium calcium
# magnesium citric salicylate menthol camphor zinc pyrithione benzalkonium
# hydrocortisone lidocaine benzocaine phenol glycerin sorbitol fructose
# bimatoprost latanoprost timolol travoprost brimonidine
# """.split()
# )
# INGREDIENT_SUFFIXES = (
#     " hydrochloride", " hcl", " phosphate", " sulfate", " citrate",
#     " sodium", " potassium", " usp", " bp", " ip", " er", " xr",
#     " sr", " cr", " ar", " mr",
# )

# def root_token(s: str) -> str:
#     s2 = re.sub(r"[^A-Za-z ]", " ", s).strip().lower()
#     parts = [p for p in s2.split() if p not in {"polistirex", "extended", "release", "suspension"}]
#     return parts[0] if parts else s2

# def is_ingredient_like(name: str) -> bool:
#     n = name.strip().lower()
#     if n in INGREDIENT_WORDS: return True
#     if any(n.endswith(suf) for suf in INGREDIENT_SUFFIXES): return True
#     if len(n.split()) == 2 and n.split()[0] in INGREDIENT_WORDS: return True
#     return False

# def is_brand_like(name: str) -> bool:
#     n = name.strip()
#     words = n.split()
#     if len(words) > 2: return False
#     if is_ingredient_like(n): return False
#     if re.search(r"\b(extended|release|suspension|tablet|syrup|solution|drops|ophthalmic)\b", n.lower()): return False
#     if len(n) <= 14 and (n[:1].isupper() and not n.isupper()): return True
#     return len(words) == 1 and len(n) <= 12 and n.isalpha()

# def penalize_ingredients(ranked: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
#     out = []
#     seen_roots = set()
#     for name, score in ranked:
#         base = score
#         if is_ingredient_like(name): base -= INGREDIENT_PENALTY
#         elif is_brand_like(name): base += BRAND_BONUS
#         r = root_token(name)
#         if r in seen_roots and not is_brand_like(name): base -= 15
#         seen_roots.add(r)
#         out.append((name, max(0, min(100, base))))
#     out = sorted(out, key=lambda x: (-x[1], -len(x[0])))
#     return out

# def keep_brands_first(ranked: List[Tuple[str, int]], limit=5) -> List[Tuple[str, int]]:
#     brands = [(n, s) for n, s in ranked if is_brand_like(n)]
#     non_brands = [(n, s) for n, s in ranked if not is_brand_like(n)]
#     return (brands + non_brands)[:limit]

# def fix_ocr_confusions(s: str) -> str:
#     t = s
#     t = re.sub(r"^l([a-z])", r"I\1", t)
#     t = re.sub(r"(?<=\w)[0O](?=\w)", "o", t)
#     t = re.sub(r"(?<=\w)rn(?=\w)", "m", t)
#     return t

# def joined_ngrams(tokens: List[str], max_n: int = 3) -> Set[str]:
#     out: Set[str] = set()
#     T = [t for t in tokens if t]
#     for n in range(2, min(max_n + 1, len(T) + 1)):
#         for i in range(len(T) - n + 1):
#             joined = "".join(T[i: i + n])
#             if len(joined) > 3 and re.search(r"[a-zA-Z]", joined):
#                 out.add(joined)
#     return out

# def enhance_image_for_ocr(image_bgr: np.ndarray) -> np.ndarray:
#     gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
#     denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
#     clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
#     contrast = clahe.apply(denoised)
#     kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
#     sharpened = cv2.filter2D(contrast, -1, kernel)
#     binary = cv2.adaptiveThreshold(
#         sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
#     )
#     kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
#     cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
#     return cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)

# def deskew_advanced(image_bgr: np.ndarray) -> np.ndarray:
#     gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
#     edges = cv2.Canny(gray, 50, 150, apertureSize=3)
#     lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=50, maxLineGap=20)
#     if lines is None: return image_bgr
#     angles = []
#     for line in lines:
#         x1, y1, x2, y2 = line[0]
#         angle = np.rad2deg(np.arctan2(y2 - y1, x2 - x1))
#         if angle < -45: angle += 90
#         elif angle > 45: angle -= 90
#         angles.append(angle)
#     if not angles: return image_bgr
#     median_angle = float(np.median(angles))
#     if abs(median_angle) < 0.5: return image_bgr
#     h, w = image_bgr.shape[:2]
#     center = (w // 2, h // 2)
#     M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
#     cos = np.abs(M[0, 0]); sin = np.abs(M[0, 1])
#     new_w = int((h * sin) + (w * cos)); new_h = int((h * cos) + (w * sin))
#     M[0, 2] += (new_w / 2) - center[0]; M[1, 2] += (new_h / 2) - center[1]
#     return cv2.warpAffine(
#         image_bgr, M, (new_w, new_h),
#         flags=cv2.INTER_CUBIC,
#         borderMode=cv2.BORDER_CONSTANT,
#         borderValue=(255, 255, 255)
#     )

# def generate_image_variants(image_bgr: np.ndarray, light: bool = True) -> List[np.ndarray]:
#     variants: List[np.ndarray] = []
#     deskewed = deskew_advanced(image_bgr.copy())
#     base = deskewed
#     enh = enhance_image_for_ocr(base)
#     gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
#     _, hi = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
#     hi_bgr = cv2.cvtColor(hi, cv2.COLOR_GRAY2BGR)
#     core = [base, enh, hi_bgr]; variants.extend(core)
#     if not light:
#         # only one heavy rotation for speed
#         variants.append(cv2.rotate(base, cv2.ROTATE_90_CLOCKWISE))
#     return variants

# def ocr_tesseract(image_bgr: np.ndarray) -> Tuple[List[str], str]:
#     if not TESS_AVAILABLE: return [], ""
#     gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
#     tokens: List[str] = []; raw_text = ""
#     try:
#         raw_text = pytesseract.image_to_string(gray, lang="eng", config=TESS_CONFIG_BASE.split(" -c")[0]) or ""
#         th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 4)
#         data = pytesseract.image_to_data(th, lang="eng", config=TESS_CONFIG_BASE, output_type=pytesseract.Output.DICT)
#         min_confidence = 60
#         for i, conf_str in enumerate(data.get("conf", [])):
#             try:
#                 conf = int(conf_str)
#                 if conf >= min_confidence:
#                     txt = (data["text"][i] or "").strip()
#                     cleaned = re.sub(r"[^\w\-.]", "", txt)
#                     if cleaned and len(cleaned) > 2 and re.search(r"[A-Za-z]", cleaned):
#                         tokens.append(cleaned)
#             except Exception:
#                 continue
#     except Exception as e:
#         logging.warning(f"Tesseract error: {e}")
#     return tokens, raw_text.strip()

# def ocr_tesseract_relaxed(image_bgr: np.ndarray) -> Tuple[List[str], str]:
#     if not TESS_AVAILABLE: return [], ""
#     tokens_all: List[str] = []; raw_all = ""
#     try:
#         big = cv2.resize(image_bgr, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
#         gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
#         gray = cv2.bilateralFilter(gray, 9, 75, 75)
#         for psm in (7, 11):
#             try:
#                 data = pytesseract.image_to_data(
#                     gray, lang="eng",
#                     config=f"--oem 1 --psm {psm} -c preserve_interword_spaces=1",
#                     output_type=pytesseract.Output.DICT,
#                 )
#                 for i, conf_str in enumerate(data.get("conf", [])):
#                     try:
#                         conf = int(conf_str)
#                         if conf >= 45:
#                             txt = (data["text"][i] or "").strip()
#                             cleaned = re.sub(r"[^\w\-]", "", txt)
#                             if cleaned and len(cleaned) > 2 and re.search(r"[A-Za-z]", cleaned):
#                                 tokens_all.append(cleaned)
#                     except Exception:
#                         continue
#                 raw = pytesseract.image_to_string(
#                     gray, lang="eng",
#                     config=f"--oem 1 --psm {psm} -c preserve_interword_spaces=1"
#                 )
#                 raw_all += " " + raw
#             except Exception:
#                 continue
#     except Exception as e:
#         logging.warning(f"Relaxed Tesseract error: {e}")
#     seen, dedup = set(), []
#     for t in tokens_all:
#         if t not in seen:
#             seen.add(t); dedup.append(t)
#     return dedup, raw_all.strip()

# def clean_text_for_ner(text: str) -> str:
#     text = re.sub(r"[^\w\s\-\%]", " ", text)
#     return re.sub(r"\s+", " ", text).strip()

# def stitch_hf_entities(entities: List[dict]) -> List[dict]:
#     merged = []; cur_word, cur_group = "", None
#     def flush():
#         nonlocal cur_word, cur_group
#         if cur_word: merged.append({"entity_group": cur_group, "word": cur_word})
#         cur_word, cur_group = "", None
#     for e in entities or []:
#         w = (e.get("word") or "").strip(); g = e.get("entity_group")
#         if not w: continue
#         if w.startswith("##"):
#             if cur_word: cur_word += w[2:]; continue
#         if g == cur_group and cur_word:
#             needs_space = cur_word[-1].isalnum() and w[0].isalnum()
#             cur_word += (" " if needs_space else "") + w
#         else:
#             flush(); cur_word, cur_group = w, g
#     flush(); return merged

# def ner_candidates(clean_text: str) -> Set[str]:
#     out: Set[str] = set()
#     if ner_pipeline is None: return out
#     try:
#         raw = ner_pipeline(clean_text); stitched = stitch_hf_entities(raw)
#         for e in stitched:
#             g, w = e.get("entity_group"), (e.get("word") or "").strip(" -.,")
#             if g in NER_ALLOWED and w and len(w) >= 3:
#                 toks = [t.lower() for t in w.split()]
#                 if toks and all(t in STOP_WORDS for t in toks): continue
#                 out.add(w)
#                 if " " in w:
#                     for p in w.split():
#                         p = p.strip(" -.,")
#                         if len(p) >= 4 and p.lower() not in STOP_WORDS and VOWEL_RE.search(p): out.add(p)
#     except Exception as e:
#         logging.warning(f"NER failed: {e}")
#     return out

# def is_blacklisted(text: str) -> bool:
#     lower = text.lower()
#     for pattern in BLACKLIST_PATTERNS:
#         if re.search(pattern, lower): return True
#     return False

# def ngrams(tokens: List[str], max_n: int = 3) -> Set[str]:
#     out: Set[str] = set()
#     toks = [t for t in tokens if t and len(t) > 1 and not t.isdigit()]
#     for n in range(1, max_n + 1):
#         for i in range(len(toks) - n + 1):
#             phrase = " ".join(toks[i: i + n])
#             if len(phrase) > 2 and re.search(r"[A-Za-z]", phrase):
#                 out.add(phrase)
#     return out

# def make_candidates(raw_text: str, tokens: List[str]) -> Set[str]:
#     candidates: Set[str] = set()
#     norm_tokens = [fix_ocr_confusions(t) for t in tokens]
#     candidates |= ngrams(norm_tokens, max_n=3)
#     for token in set(tokens + norm_tokens):
#         if len(token) >= 3 and re.search(r"[A-Za-z]", token):
#             candidates.add(token)
#     candidates |= joined_ngrams(norm_tokens, max_n=3)
#     candidates |= ner_candidates(clean_text_for_ner(raw_text))

#     cleaned: Set[str] = set()
#     for cand in candidates:
#         cand = cand.strip(" -.,")
#         if len(cand) < 3 or cand.isdigit() or not re.search(r"[A-Za-z]", cand): continue
#         words = [w.lower() for w in cand.split()]
#         if words and all(w in STOP_WORDS for w in words): continue
#         if is_blacklisted(cand): continue
#         cleaned.add(cand)
#     return cleaned

# def reasonable_overlap(a: str, b: str) -> bool:
#     A, B = a.lower(), b.lower(); best = 0
#     dp = [[0] * (len(B) + 1) for _ in range(len(A) + 1)]
#     for i in range(1, len(A) + 1):
#         for j in range(1, len(B) + 1):
#             if A[i - 1] == B[j - 1]:
#                 dp[i][j] = dp[i - 1][j - 1] + 1; best = max(best, dp[i][j])
#     if best >= 5: return True
#     ta = [t for t in re.split(r"[^\w]+", A) if len(t) >= 5]
#     tb = [t for t in re.split(r"[^\w]+", B) if len(t) >= 5]
#     return bool(set(ta) & set(tb))

# def filter_drug_list(all_drug_names: List[str]) -> List[str]:
#     filtered = []
#     for name in all_drug_names:
#         if is_blacklisted(name): continue
#         if len(name.split()) > 4: continue
#         lower = name.lower()
#         if any(x in lower for x in ["bayer", "brand", "compare to"]): continue
#         filtered.append(name)
#     return filtered

# def best_drug_matches(
#     candidates: Set[str],
#     all_drug_names: List[str],
#     min_score: int = 85,
#     topk: int = 10,
#     _db_lower_to_orig: Dict[str, str] | None = None,
#     _db_keys: List[str] | None = None,
# ) -> List[Tuple[str, int]]:
#     if not candidates or not all_drug_names:
#         return []
#     if _db_lower_to_orig is None:
#         _db_lower_to_orig = {n.lower(): n for n in all_drug_names}
#     if _db_keys is None:
#         _db_keys = list(_db_lower_to_orig.keys())

#     matches: dict[str, float] = {}
#     for candidate in sorted(candidates, key=len, reverse=True):
#         best_db_key = None
#         best_score = -1.0
#         c_low = candidate.lower()

#         if c_low in _db_lower_to_orig:
#             best_db_key = c_low; best_score = 100.0
#         else:
#             result = process.extractOne(
#                 c_low, _db_keys, scorer=fuzz.token_sort_ratio, score_cutoff=min_score
#             )
#             if result:
#                 match_key, score = result[0], float(result[1])
#                 match_name_orig = _db_lower_to_orig[match_key]
#                 if reasonable_overlap(candidate, match_name_orig):
#                     best_db_key = match_key; best_score = score

#         if best_db_key:
#             db_name_orig = _db_lower_to_orig[best_db_key]
#             if db_name_orig not in matches or best_score > matches[db_name_orig]:
#                 matches[db_name_orig] = best_score

#     ranked = sorted(matches.items(), key=lambda x: (-x[1], -len(x[0])))
#     ranked = penalize_ingredients(ranked)
#     return ranked[:topk]

# # -----------------------------
# # Speed helpers
# # -----------------------------
# def _resize_safe(bgr: np.ndarray) -> np.ndarray:
#     h, w = bgr.shape[:2]
#     if h > MAX_IMAGE_HEIGHT:
#         scale = MAX_IMAGE_HEIGHT / float(h)
#         return cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
#     return bgr

# def _phash_from_pil(pil_image: Image.Image) -> str:
#     arr = np.array(pil_image)
#     return "ocr:img:" + hashlib.sha1(arr.tobytes()).hexdigest()

# def _process_one_image(
#     image_file,
#     all_drug_names: List[str],
#     db_lower_to_orig: Dict[str, str],
#     db_keys: List[str],
# ) -> tuple[str | None, dict]:
#     image_file.seek(0)
#     pil_image = Image.open(image_file).convert("RGB")
#     cache_key = _phash_from_pil(pil_image)

#     cached = cache.get(cache_key)
#     if cached:
#         return cached["top_name"], cached["dbg"]

#     base_bgr = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
#     base_bgr = _resize_safe(base_bgr)

#     # Light pass
#     variants = generate_image_variants(base_bgr, light=True)
#     image_candidates: Set[str] = set()
#     best_variant_tokens: List[str] = []
#     raw_texts: List[str] = []
#     for variant in variants:
#         tokens, raw_text = ocr_tesseract(variant)
#         if len(tokens) > len(best_variant_tokens): best_variant_tokens = tokens
#         image_candidates |= make_candidates(raw_text, tokens)
#         if raw_text: raw_texts.append(raw_text)

#     matches = best_drug_matches(
#         image_candidates, all_drug_names, min_score=PER_IMAGE_MIN_SCORE, topk=5,
#         _db_lower_to_orig=db_lower_to_orig, _db_keys=db_keys
#     )
#         # --- ADD THE SECOND LOG LINE HERE ---
#     logging.info(f"[DEBUG] Top 5 matches for this image: {matches}")

#     matches = keep_brands_first(matches, limit=5)
#     matches = [(n, s) for n, s in matches if not is_manufacturer(n)]

#     # Early exit
#     if matches and matches[0][1] >= EARLY_EXIT_SCORE and len(best_variant_tokens) >= MIN_TOKENS_FOR_CONFIDENCE:
#         dbg = {
#             "tokens_count": len(best_variant_tokens),
#             "candidates_count": len(image_candidates),
#             "matches": [{"name": m[0], "score": m[1]} for m in matches],
#             "early_exit": True,
#         }
#         top = matches[0][0]
#         cache.set(cache_key, {"top_name": top, "dbg": dbg}, timeout=CACHE_OCR_SECONDS)
#         return top, dbg

#     # One heavy rotation
#     more_variants = generate_image_variants(base_bgr, light=False)
#     if len(more_variants) > len(variants):
#         variant = more_variants[len(variants)]
#         tokens, raw_text = ocr_tesseract(variant)
#         if len(tokens) > len(best_variant_tokens): best_variant_tokens = tokens
#         image_candidates |= make_candidates(raw_text, tokens)
#         if raw_text: raw_texts.append(raw_text)

#     # Relaxed pass only if weak
#     if len(best_variant_tokens) < MIN_TOKENS_FOR_CONFIDENCE and not (matches and matches[0][1] >= 85):
#         r_tokens, r_raw = ocr_tesseract_relaxed(base_bgr)
#         if len(r_tokens) > len(best_variant_tokens): best_variant_tokens = r_tokens
#         image_candidates |= make_candidates(r_raw or "", r_tokens)
#         if r_raw: raw_texts.append(r_raw)

#     matches = best_drug_matches(
#         image_candidates, all_drug_names, min_score=PER_IMAGE_MIN_SCORE, topk=5,
#         _db_lower_to_orig=db_lower_to_orig, _db_keys=db_keys
#     )
#     matches = keep_brands_first(matches, limit=5)
#     matches = [(n, s) for n, s in matches if not is_manufacturer(n)]

#     dbg = {
#         "tokens_count": len(best_variant_tokens),
#         "candidates_count": len(image_candidates),
#         "matches": [{"name": m[0], "score": m[1]} for m in matches],
#         "early_exit": False,
#     }
#     top = matches[0][0] if matches else None
#     if top:
#         cache.set(cache_key, {"top_name": top, "dbg": dbg}, timeout=CACHE_OCR_SECONDS)
#     return top, dbg

# # -----------------------------
# # View
# # -----------------------------
# class ScanAndCheckView(APIView):
#     """
#     OCR-based drug/brand extraction (Tesseract-only, brand-first).
#     Uses local Interaction DB (DDInter import) for DDI.
#     """
#     parser_classes = (MultiPartParser, FormParser)

#     def post(self, request, *args, **kwargs):
#         image_files = request.FILES.getlist("images")
#         if not image_files:
#             return Response({"error": "No image files provided."}, status=400)

#             # Cache and precompute name keys
#         all_drug_names = cache.get("filtered_drug_names")
#         if not all_drug_names:
#             # 1. Get all global drug names
#             global_names = set(Drug.objects.values_list("name", flat=True))

#             # 2. Get all local Kenyan brand names
#             local_names = set(LocalBrand.objects.values_list("brand_name", flat=True))

#             # 3. Combine them into one list
#             # We use .lower() for the set to remove case-sensitive duplicates
#             combined_names_lower = {name.lower() for name in global_names}
#             combined_names_final = list(global_names)

#             for name in local_names:
#                 if name.lower() not in combined_names_lower:
#                     combined_names_final.append(name)

#             # 4. Filter the final list
#             all_drug_names = filter_drug_list(combined_names_final)

#             logging.info(f"Rebuilt drug name cache: {len(global_names)} global, {len(local_names)} local, {len(all_drug_names)} final unique names.")

#             cache.set("filtered_drug_names", all_drug_names, timeout=3600)

#         db_lower_to_orig = {n.lower(): n for n in all_drug_names}
#         db_keys = list(db_lower_to_orig.keys())

#         logging.info("\n" + "=" * 60)
#         logging.info(f"[INFO] Processing {len(image_files)} images")
#         logging.info(f"[INFO] Searching against {len(all_drug_names)} pharmaceutical names")
#         logging.info("=" * 60 + "\n")

#         per_image_results: List[dict] = []
#         final_names: List[str] = []

#         # Parallel per-image
#         with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
#             futures = [
#                 ex.submit(_process_one_image, f, all_drug_names, db_lower_to_orig, db_keys)
#                 for f in image_files
#             ]
#             for fut in as_completed(futures):
#                 try:
#                     top_name, dbg = fut.result()
#                     if top_name:
#                         final_names.append(top_name)
#                     per_image_results.append(dbg)
#                 except Exception as e:
#                     logging.error(f"[ERROR] Worker failed: {e}", exc_info=True)
#                     return Response({"error": "Server error processing an image."}, status=500)

#         # Dedup, cap
#         seen = set(); ordered = []
#         for n in final_names:
#             if n not in seen:
#                 ordered.append(n); seen.add(n)
#         final_drug_names = ordered[:FINAL_MAX_RESULTS]

#         logging.info("\n" + "=" * 60)
#         if final_drug_names:
#             logging.info(f"[RESULT] Identified {len(final_drug_names)} drugs (Unique top picks per image):")
#             for n in final_drug_names:
#                 logging.info(f"  • {n}")
#         else:
#             logging.info("[RESULT] No drugs identified")
#         logging.info("=" * 60 + "\n")

#         if not final_drug_names:
#             return Response(
#                 {
#                     "error": "No known medication names were identified in the images.",
#                     "found_drug_names": [],
#                     "debug_info": {"per_image_results": per_image_results},
#                 },
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         payload = self._pack_payload(final_drug_names)
#         payload["debug_info"] = {"per_image_results": per_image_results}

#         # Trim debug in production if you want
#         if os.getenv("ENV") == "prod":
#             payload["debug_info"] = {"summary": {
#                 "images": len(image_files),
#                 "found": len(final_drug_names),
#             }}

#         return Response(payload, status=status.HTTP_200_OK)

#     # THIS IS CHANGE 2: Replace your old function with this
#     def _pack_payload(self, drug_names: List[str]) -> dict:
#         """
#         Package drug information and interactions using the LOCAL DB
#         and the new LOCAL BRAND mapping.
#         """
#         payload = {"found_drug_names": drug_names}

#         # --- THIS IS THE NEW LOGIC ---

#         # 1. Create the final list of ingredients to check
#         generic_names_to_check = set()
#         all_drug_objects_in_db = []

#         for name in drug_names:
#             name_lower = name.lower()

#             # Check 1: Is it a global brand/generic in our main Drug table?
#             try:
#                 drug_obj = Drug.objects.get(name__iexact=name_lower)
#                 all_drug_objects_in_db.append(drug_obj)
#                 generic_names_to_check.add(drug_obj.name) 
#                 continue # Found it, move to next name
#             except Drug.DoesNotExist:
#                 pass # Not in Drug table, check LocalBrand table

#             # Check 2: Is it a local Kenyan brand?
#             try:
#                 local_brand_obj = LocalBrand.objects.get(brand_name__iexact=name_lower)
#                 # It is! Get its ingredients, e.g., ["Paracetamol", "Caffeine"]
#                 ingredients = local_brand_obj.generic_names
#                 for ingredient in ingredients:
#                     generic_names_to_check.add(ingredient)

#                 # Try to get the Drug objects for the ingredients
#                 ingredient_objs = Drug.objects.filter(name__in=ingredients)
#                 all_drug_objects_in_db.extend(list(ingredient_objs))

#                 logging.info(f"Mapped local brand '{name}' to ingredients: {ingredients}")

#             except LocalBrand.DoesNotExist:
#                 logging.warning(f"'{name}' not found in Drug table or LocalBrand table. Skipping.")

#         # --- END OF NEW LOGIC ---

#         # Fetch Details from DB for found names
#         unique_drug_objects = list({obj.id: obj for obj in all_drug_objects_in_db}.values())
#         payload["drug_details"] = DrugSerializer(unique_drug_objects, many=True).data

#         # --- LOCAL DATABASE Interaction Check ---
#         local_interactions = []
#         final_ingredient_list = list(generic_names_to_check)

#         if len(final_ingredient_list) >= 2:
#             logging.info(f"Checking LOCAL DB for interactions among ingredients: {final_ingredient_list}")

#             # Call the static method with the *ingredient* list
#             local_interactions = Interaction.get_interactions(final_ingredient_list)

#         else:
#             logging.info("Less than 2 unique ingredients found, skipping interaction check.")

#         payload["interactions"] = local_interactions
#         # ---------------------------------

#         return payload
# backend/drugs/views.py
# from __future__ import annotations

# import os
# import re
# import platform
# import hashlib
# import logging
# from itertools import combinations
# from typing import List, Set, Tuple, Dict
# import json # <-- NEW IMPORT

# import numpy as np
# import cv2
# from PIL import Image
# import pytesseract

# from django.core.cache import cache
# from django.db.models import Q # Make sure Q is imported
# from rest_framework import status
# from rest_framework.parsers import FormParser, MultiPartParser
# from rest_framework.response import Response
# from rest_framework.views import APIView

# from concurrent.futures import ThreadPoolExecutor, as_completed
# from rapidfuzz import fuzz, process

# # --- THIS IS THE CORRECTED IMPORT BLOCK ---
# from .models import Drug, Interaction, DrugInfo, LocalBrand
# from .serializers import DrugSerializer, InteractionSerializer
# # ------------------------------------------
# # --- NEW: AI Summarizer Imports ---
# # We use the HfApi to call a model without downloading it.
# # This requires a Hugging Face API token in your .env file
# # (HF_TOKEN = "hf_...")
# from huggingface_hub import HfApi
# from huggingface_hub import InferenceClient # <-- THE FIX
# from huggingface_hub.utils import hf_raise_for_status
# from huggingface_hub.errors import BadRequestError
# # ----------------------------------

# logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(asctime)s:%(message)s")

# # --- NEW: AI Summarizer Config ---
# # We will use a model fine-tuned for summarization.
# # BioMistral is great but complex to host. We'll start with a
# # reliable summarizer, as your proposal suggests, to
# # "generate user-friendly reports".
# # This model is a standard for text summarization.
# # --- NEW: AI Summarizer Config ---
# # ...
# AI_MODEL_NAME = "facebook/bart-large-cnn"
# HF_TOKEN = os.getenv("HF_TOKEN")
# SUMMARIZER_API = None
# if HF_TOKEN:
#     try:
#         HfApi().whoami(token=HF_TOKEN) # Test the token
#         SUMMARIZER_API = InferenceClient(model=AI_MODEL_NAME, token=HF_TOKEN) # <-- THE FIX
#         logging.info(f"Hugging Face Summarizer ({AI_MODEL_NAME}) initialized.")
#     # ...
#     except Exception as e:
#         logging.error(f"Failed to initialize Hugging Face API. AI Summaries will be disabled. Error: {e}")
# else:
#     logging.warning("HF_TOKEN not set in .env file. AI Summaries will be disabled.")
# # ---------------------------------

# # logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(asctime)s:%(message)s")

# # -----------------------------
# # Tunables (Unchanged)
# # -----------------------------
# PER_IMAGE_MIN_SCORE = 78
# GLOBAL_MIN_SCORE    = 85
# PER_IMAGE_FINAL_TOPK = 1
# FINAL_MAX_RESULTS    = 10
# INGREDIENT_PENALTY   = 10
# BRAND_BONUS          = 5

# EARLY_EXIT_SCORE = 92            # if first-pass top score >= this, skip heavy passes
# MIN_TOKENS_FOR_CONFIDENCE = 4    # tokens threshold for trusting first pass
# MAX_IMAGE_HEIGHT = 1200          # downscale tall images to speed OCR
# MAX_WORKERS = min(4, (os.cpu_count() or 2))
# CACHE_OCR_SECONDS = 24 * 3600
# ENABLE_PADDLE = bool(int(os.getenv("ENABLE_PADDLE", "0")))

# VOWEL_RE = re.compile(r"[aeiouyAEIOUY]")

# # -----------------------------
# # NER (optional; no impact if unavailable)
# # -----------------------------
# NER_ALLOWED = {"Medication", "Drug"}
# ner_pipeline = None
# try:
#     from transformers import pipeline as hf_make_pipeline
#     from transformers import logging as hf_logging
#     hf_logging.set_verbosity_error()
#     ner_pipeline = hf_make_pipeline(
#         "ner", model="d4data/biomedical-ner-all", aggregation_strategy="simple"
#     )
#     logging.info("HF biomedical NER loaded.")
# except Exception as e:
#     ner_pipeline = None
#     logging.warning(f"transformers not installed or NER init failed: {e}")

# # -----------------------------
# # PaddleOCR (strictly opt-in)
# # -----------------------------
# PADDLE_AVAILABLE = False
# OCR_ENGINE = None
# if ENABLE_PADDLE:
#     try:
#         from paddleocr import PaddleOCR
#         PADDLE_AVAILABLE = True
#         try:
#             OCR_ENGINE = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
#             logging.info("PaddleOCR initialized.")
#         except TypeError:
#             logging.warning("PaddleOCR version mismatch; retrying without show_log.")
#             OCR_ENGINE = PaddleOCR(use_angle_cls=True, lang="en")
#     except Exception as e:
#         logging.warning(f"PaddleOCR not available: {e}")
#         OCR_ENGINE = None

# # -----------------------------
# # Tesseract config (Unchanged)
# # -----------------------------
# TESS_AVAILABLE = True
# TESS_CONFIG_BASE = ""
# TESS_CONFIG_LINE = ""
# try:
#     tessdata_dir_config = ""
#     if platform.system() == "Windows":
#         tesseract_exe_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
#         tessdata_path = r"C:\Program Files\Tesseract-OCR\tessdata"
#         if os.path.exists(tesseract_exe_path) and os.path.isdir(tessdata_path):
#             pytesseract.pytesseract.tesseract_cmd = tesseract_exe_path
#             tessdata_dir_config = f'--tessdata-dir "{tessdata_path}"'
#             logging.info("Tesseract configured.")
#         else:
#             logging.warning("Tesseract exe/tessdata not found.")
#             TESS_AVAILABLE = False
#     else:
#         pytesseract.get_tesseract_version()
#         logging.info("Tesseract found in PATH.")

#     if TESS_AVAILABLE:
#         TESS_CONFIG_BASE = f'{tessdata_dir_config} --oem 1 --psm 6 -c preserve_interword_spaces=1'
#         TESS_CONFIG_LINE = f'{tessdata_dir_config} --oem 1 --psm 7 -c preserve_interword_spaces=1'
# except Exception as e:
#     logging.warning(f"Tesseract config error: {e}")
#     TESS_AVAILABLE = False

# # -----------------------------
# # Heuristics & filters (Unchanged)
# # -----------------------------
# STOP_WORDS = set(
#     x.lower()
#     for x in """
# for oral use only day night extended release suspension suppressant
# tablet tablets liquid syrup solution capsules capsule mg ml strength dose doses
# adult adults children warning warnings facts inactive active ingredients ingredient
# supplement purposes purpose directions drug keep out reach of children hour
# hours net wt contents by and flavored flavor alcohol-free orange ndc code
# gastro-resistant coated enteric pain reliever fever reducer cough relief overnight
# pharmaceuticals pharma inc ltd llp gmbh co kg corporation corp incorporated company co
# lotion cream ointment spray drops nasal ophthalmic topical transdermal patch
# prescription only over-the-counter otc pharmacy medication medicine sample patient
# store at room temperature protect from light moisture avoid freezing see insert
# shake well before using discard after lot exp date manufactured distributed by made in
# daily weekly monthly take with food water empty stomach hours apart as directed doctor
# healthcare provider do not exceed recommended dosage if symptoms persist consult
# may cause drowsiness dizziness allergy alert stop use ask side effects interactions
# call poison control center emergency medical help questions comments visit website
# new improved formula compare to active ingredient of original maximum strength regular
# sodium free sugar free gluten free non drowsy dye free fast acting long lasting hour
# relief of headache fever cold flu allergy sinus congestion nausea vomiting diarrhea pain
# inflammation itching rash swelling redness irritation dryness burning stomach upset
# heartburn constipation acid indigestion sleeplessness anxiety depression
# adhd high blood pressure cholesterol diabetes thyroid asthma arthritis osteoporosis
# infection vitamins minerals electrolytes extract whole aloe vera natural herbal
# botanical plant based organic derived compound blend complex mixture combination
# seed oil root leaf flower fruit bark stem peg ppg methoxy dimethicone chestnut horse
# bayer brand name generic compare equivalent
# low dose compare active ingredient nsaid delayed-release delayed release
# enteric coated safety coated safety regimen actual size drug facts
# sterile sterilely ophthalmic ophthalmology eye drops solution drops rinse
# mist mouthwash antiseptic multi-dose multiuse multi use preservative-free
# care healthcare
# """.split() # <-- NOTE: Adding "care" and "healthcare" is still a good idea!
# )
# STOP_WORDS |= set(
#     """
# alcon novartis pfizer merck bayer sanofi roche gsk glaxosmithkline takeda
# teva abbvie astrazeneca johnson johnson j j eli lilly lilly allergan globus labs
# sun pharma cipla dr reddys reddy apotex sandoz lupin zydus
# ophthalmic sterile ophthalmology eye drops solution drops rinse
# """.split()
# )
# # Add common packaging/manufacturer fragments that appear in OCR noise
# STOP_WORDS |= {"aspen", "care", "relief", "healthcare", "mara", "moja","rid"}

# BLACKLIST_PATTERNS = [
#     r"aloe\s+vera", r"horse\s+chestnut", r"peg[-\s]?ppg", r"dimethicone", r"methoxy",
#     r"\d+[-\s]+aminopropyl", r"whole\s+extract", r"seed\s+extract", r"essential\s+oil",
#     r"carrier\s+oil", r"\blister\b", r"\bmouthwash\b", r"\blisterine\b", r"\balcon\b",
#     r"\ballergan\b", r"\bglobus\b", r"\bglobus\s+labs\b", r"\bnovartis\b", r"\bgsk\b",
#     r"\bglaxosmithkline\b",
# ]
# MANUFACTURER_WORDS = set("alcon allergan novartis bayer pfizer merck sanofi gsk lilly globus sandoz teva".split())
# def is_manufacturer(word: str) -> bool:
#     return word.strip().lower() in MANUFACTURER_WORDS

# INGREDIENT_WORDS = set(
#     x.lower()
#     for x in """
# acetaminophen paracetamol ibuprofen naproxen aspirin guaifenesin
# dextromethorphan pseudoephedrine phenylephrine diphenhydramine doxylamine
# cetirizine loratadine fexofenadine amoxicillin clavulanate azithromycin
# metformin atorvastatin simvastatin omeprazole esomeprazole lansoprazole
# polistirex hydrochloride hcl phosphate sulfate sodium potassium calcium
# magnesium citric salicylate menthol camphor zinc pyrithione benzalkonium
# hydrocortisone lidocaine benzocaine phenol glycerin sorbitol fructose
# bimatoprost latanoprost timolol travoprost brimonidine
# """.split()
# )
# INGREDIENT_SUFFIXES = (
#     " hydrochloride", " hcl", " phosphate", " sulfate", " citrate",
#     " sodium", " potassium", " usp", " bp", " ip", " er", " xr",
#     " sr", " cr", " ar", " mr",
# )

# def root_token(s: str) -> str:
#     s2 = re.sub(r"[^A-Za-z ]", " ", s).strip().lower()
#     parts = [p for p in s2.split() if p not in {"polistirex", "extended", "release", "suspension"}]
#     return parts[0] if parts else s2

# def is_ingredient_like(name: str) -> bool:
#     n = name.strip().lower()
#     if n in INGREDIENT_WORDS: return True
#     if any(n.endswith(suf) for suf in INGREDIENT_SUFFIXES): return True
#     if len(n.split()) == 2 and n.split()[0] in INGREDIENT_WORDS: return True
#     return False

# def is_brand_like(name: str) -> bool:
#     n = name.strip()
#     words = n.split()
#     if len(words) > 2: return False
#     if is_ingredient_like(n): return False
#     if re.search(r"\b(extended|release|suspension|tablet|syrup|solution|drops|ophthalmic)\b", n.lower()): return False
#     if len(n) <= 14 and (n[:1].isupper() and not n.isupper()): return True
#     return len(words) == 1 and len(n) <= 12 and n.isalpha()

# def penalize_ingredients(ranked: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
#     out = []
#     seen_roots = set()
#     for name, score in ranked:
#         base = score
#         if is_ingredient_like(name): base -= INGREDIENT_PENALTY
#         elif is_brand_like(name): base += BRAND_BONUS
#         r = root_token(name)
#         if r in seen_roots and not is_brand_like(name): base -= 15
#         seen_roots.add(r)
#         out.append((name, max(0, min(100, base))))
#     out = sorted(out, key=lambda x: (-x[1], -len(x[0])))
#     return out

# def keep_brands_first(ranked: List[Tuple[str, int]], limit=5) -> List[Tuple[str, int]]:
#     brands = [(n, s) for n, s in ranked if is_brand_like(n)]
#     non_brands = [(n, s) for n, s in ranked if not is_brand_like(n)]
#     return (brands + non_brands)[:limit]

# def fix_ocr_confusions(s: str) -> str:
#     t = s
#     t = re.sub(r"^l([a-z])", r"I\1", t)
#     t = re.sub(r"(?<=\w)[0O](?=\w)", "o", t)
#     t = re.sub(r"(?<=\w)rn(?=\w)", "m", t)
#     return t

# def joined_ngrams(tokens: List[str], max_n: int = 3) -> Set[str]:
#     out: Set[str] = set()
#     T = [t for t in tokens if t]
#     for n in range(2, min(max_n + 1, len(T) + 1)):
#         for i in range(len(T) - n + 1):
#             joined = "".join(T[i: i + n])
#             if len(joined) > 3 and re.search(r"[a-zA-Z]", joined):
#                 out.add(joined)
#     return out

# def enhance_image_for_ocr(image_bgr: np.ndarray) -> np.ndarray:
#     gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
#     denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
#     clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
#     contrast = clahe.apply(denoised)
#     kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
#     sharpened = cv2.filter2D(contrast, -1, kernel)
#     binary = cv2.adaptiveThreshold(
#         sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
#     )
#     kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
#     cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
#     return cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)

# def deskew_advanced(image_bgr: np.ndarray) -> np.ndarray:
#     gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
#     edges = cv2.Canny(gray, 50, 150, apertureSize=3)
#     lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=50, maxLineGap=20)
#     if lines is None: return image_bgr
#     angles = []
#     for line in lines:
#         x1, y1, x2, y2 = line[0]
#         angle = np.rad2deg(np.arctan2(y2 - y1, x2 - x1))
#         if angle < -45: angle += 90
#         elif angle > 45: angle -= 90
#         angles.append(angle)
#     if not angles: return image_bgr
#     median_angle = float(np.median(angles))
#     if abs(median_angle) < 0.5: return image_bgr
#     h, w = image_bgr.shape[:2]
#     center = (w // 2, h // 2)
#     M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
#     cos = np.abs(M[0, 0]); sin = np.abs(M[0, 1])
#     new_w = int((h * sin) + (w * cos)); new_h = int((h * cos) + (w * sin))
#     M[0, 2] += (new_w / 2) - center[0]; M[1, 2] += (new_h / 2) - center[1]
#     return cv2.warpAffine(
#         image_bgr, M, (new_w, new_h),
#         flags=cv2.INTER_CUBIC,
#         borderMode=cv2.BORDER_CONSTANT,
#         borderValue=(255, 255, 255)
#     )

# def generate_image_variants(image_bgr: np.ndarray, light: bool = True) -> List[np.ndarray]:
#     variants: List[np.ndarray] = []
#     deskewed = deskew_advanced(image_bgr.copy())
#     base = deskewed
#     enh = enhance_image_for_ocr(base)
#     gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
#     _, hi = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
#     hi_bgr = cv2.cvtColor(hi, cv2.COLOR_GRAY2BGR)
#     core = [base, enh, hi_bgr]; variants.extend(core)
#     if not light:
#         # only one heavy rotation for speed
#         variants.append(cv2.rotate(base, cv2.ROTATE_90_CLOCKWISE))
#     return variants

# def ocr_tesseract(image_bgr: np.ndarray) -> Tuple[List[str], str]:
#     if not TESS_AVAILABLE: return [], ""
#     gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
#     tokens: List[str] = []; raw_text = ""
#     try:
#         raw_text = pytesseract.image_to_string(gray, lang="eng", config=TESS_CONFIG_BASE.split(" -c")[0]) or ""
#         th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 4)
#         data = pytesseract.image_to_data(th, lang="eng", config=TESS_CONFIG_BASE, output_type=pytesseract.Output.DICT)
#         min_confidence = 60
#         for i, conf_str in enumerate(data.get("conf", [])):
#             try:
#                 conf = int(conf_str)
#                 if conf >= min_confidence:
#                     txt = (data["text"][i] or "").strip()
#                     cleaned = re.sub(r"[^\w\-.]", "", txt)
#                     if cleaned and len(cleaned) > 2 and re.search(r"[A-Za-z]", cleaned):
#                         tokens.append(cleaned)
#             except Exception:
#                 continue
#     except Exception as e:
#         logging.warning(f"Tesseract error: {e}")
#     return tokens, raw_text.strip()

# def ocr_tesseract_relaxed(image_bgr: np.ndarray) -> Tuple[List[str], str]:
#     if not TESS_AVAILABLE: return [], ""
#     tokens_all: List[str] = []; raw_all = ""
#     try:
#         big = cv2.resize(image_bgr, None, fx=1.8, fy=1.8, interpolation=cv2.INTER_CUBIC)
#         gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
#         gray = cv2.bilateralFilter(gray, 9, 75, 75)
#         for psm in (7, 11):
#             try:
#                 data = pytesseract.image_to_data(
#                     gray, lang="eng",
#                     config=f"--oem 1 --psm {psm} -c preserve_interword_spaces=1",
#                     output_type=pytesseract.Output.DICT,
#                 )
#                 for i, conf_str in enumerate(data.get("conf", [])):
#                     try:
#                         conf = int(conf_str)
#                         if conf >= 45:
#                             txt = (data["text"][i] or "").strip()
#                             cleaned = re.sub(r"[^\w\-]", "", txt)
#                             if cleaned and len(cleaned) > 2 and re.search(r"[A-Za-z]", cleaned):
#                                 tokens_all.append(cleaned)
#                     except Exception:
#                         continue
#                 raw = pytesseract.image_to_string(
#                     gray, lang="eng",
#                     config=f"--oem 1 --psm {psm} -c preserve_interword_spaces=1"
#                 )
#                 raw_all += " " + raw
#             except Exception:
#                 continue
#     except Exception as e:
#         logging.warning(f"Relaxed Tesseract error: {e}")
#     seen, dedup = set(), []
#     for t in tokens_all:
#         if t not in seen:
#             seen.add(t); dedup.append(t)
#     return dedup, raw_all.strip()

# def clean_text_for_ner(text: str) -> str:
#     text = re.sub(r"[^\w\s\-\%]", " ", text)
#     return re.sub(r"\s+", " ", text).strip()

# def stitch_hf_entities(entities: List[dict]) -> List[dict]:
#     merged = []; cur_word, cur_group = "", None
#     def flush():
#         nonlocal cur_word, cur_group
#         if cur_word: merged.append({"entity_group": cur_group, "word": cur_word})
#         cur_word, cur_group = "", None
#     for e in entities or []:
#         w = (e.get("word") or "").strip(); g = e.get("entity_group")
#         if not w: continue
#         if w.startswith("##"):
#             if cur_word: cur_word += w[2:]; continue
#         if g == cur_group and cur_word:
#             needs_space = cur_word[-1].isalnum() and w[0].isalnum()
#             cur_word += (" " if needs_space else "") + w
#         else:
#             flush(); cur_word, cur_group = w, g
#     flush(); return merged

# def ner_candidates(clean_text: str) -> Set[str]:
#     out: Set[str] = set()
#     if ner_pipeline is None: return out
#     try:
#         raw = ner_pipeline(clean_text); stitched = stitch_hf_entities(raw)
#         for e in stitched:
#             g, w = e.get("entity_group"), (e.get("word") or "").strip(" -.,")
#             if g in NER_ALLOWED and w and len(w) >= 3:
#                 toks = [t.lower() for t in w.split()]
#                 if toks and all(t in STOP_WORDS for t in toks): continue
#                 out.add(w)
#                 if " " in w:
#                     for p in w.split():
#                         p = p.strip(" -.,")
#                         if len(p) >= 4 and p.lower() not in STOP_WORDS and VOWEL_RE.search(p): out.add(p)
#     except Exception as e:
#         logging.warning(f"NER failed: {e}")
#     return out

# def is_blacklisted(text: str) -> bool:
#     lower = text.lower()
#     for pattern in BLACKLIST_PATTERNS:
#         if re.search(pattern, lower): return True
#     return False

# def ngrams(tokens: List[str], max_n: int = 3) -> Set[str]:
#     out: Set[str] = set()
#     toks = [t for t in tokens if t and len(t) > 1 and not t.isdigit()]
#     for n in range(1, max_n + 1):
#         for i in range(len(toks) - n + 1):
#             phrase = " ".join(toks[i: i + n])
#             if len(phrase) > 2 and re.search(r"[A-Za-z]", phrase):
#                 out.add(phrase)
#     return out
# def _split_camel_and_junk(s: str) -> Set[str]:
#     """
#     Produce reasonable splits from CamelCase/merged strings:
#       'MoJAMARaspe' -> {'MoJA', 'MAR', 'aspe', 'MoJA MAR', 'MAR aspe', 'MoJA MAR aspe'}
#     Also normalize to lower-case variants for matching.
#     """
#     out = set()
#     if not s: return out
#     # Insert spaces at camel boundaries and between letters/digits
#     s1 = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
#     s1 = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", s1)
#     s1 = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", s1)
#     # Remove repeated non-letters at ends
#     s1 = re.sub(r"[^A-Za-z\s]+", " ", s1)
#     parts = [p.strip() for p in re.split(r"[\s_]+", s1) if p.strip()]
#     # create ngrams and joined forms
#     for n in range(1, min(4, len(parts) + 1)):
#         for i in range(len(parts) - n + 1):
#             seg = parts[i : i + n]
#             out.add(" ".join(seg))
#             out.add("".join(seg))
#     # also add lower-cased tokens & short tokens
#     out = set(x for x in out if len(re.sub(r"[^A-Za-z]", "", x)) >= 2)
#     out |= set(x.lower() for x in list(out))
#     return out


# def make_candidates(raw_text: str, tokens: List[str]) -> Set[str]:
#     candidates: Set[str] = set()
#     # Normal token fixes
#     norm_tokens = [fix_ocr_confusions(t) for t in tokens]
#     candidates |= ngrams(norm_tokens, max_n=3)
#     for token in set(tokens + norm_tokens):
#         if len(token) >= 3 and re.search(r"[A-Za-z]", token):
#             candidates.add(token)
#             # also add camel-splits/merged variants for this token
#             candidates |= _split_camel_and_junk(token)

#     # also derive candidates from raw_text words and camel/joined variants there
#     if raw_text:
#         # strip unusual chars then take word ngrams
#         cleaned_raw = re.sub(r"[^A-Za-z0-9\s]", " ", raw_text)
#         words = [w.strip() for w in re.split(r"[\s]+", cleaned_raw) if len(w.strip()) >= 2]
#         # add ngrams with spaces (helpful for 'MARA MOJA' when OCR splits)
#         for n in range(1, min(4, len(words) + 1)):
#             for i in range(len(words) - n + 1):
#                 cand = " ".join(words[i : i + n])
#                 if len(re.sub(r"[^A-Za-z]", "", cand)) >= 3:
#                     candidates.add(cand)
#                 # and camel/joined variants
#                 candidates |= _split_camel_and_junk(cand)

#     # NER-based candidates (unchanged)
#     candidates |= joined_ngrams(norm_tokens, max_n=3)
#     candidates |= ner_candidates(clean_text_for_ner(raw_text))

#     cleaned: Set[str] = set()
#     for cand in candidates:
#         cand = cand.strip(" -.,")
#         if len(cand) < 3 or cand.isdigit() or not re.search(r"[A-Za-z]", cand):
#             continue
#         words = [w.lower() for w in cand.split()]
#         if words and all(w in STOP_WORDS for w in words):
#             continue
#         if is_blacklisted(cand):
#             continue
#         # collapse multiple internal spaces
#         cand = re.sub(r"\s+", " ", cand).strip()
#         cleaned.add(cand)
#     return cleaned

# def reasonable_overlap(a: str, b: str) -> bool:
#     A, B = a.lower(), b.lower(); best = 0
#     dp = [[0] * (len(B) + 1) for _ in range(len(A) + 1)]
#     for i in range(1, len(A) + 1):
#         for j in range(1, len(B) + 1):
#             if A[i - 1] == B[j - 1]:
#                 dp[i][j] = dp[i - 1][j - 1] + 1; best = max(best, dp[i][j])
#     if best >= 5: return True
#     ta = [t for t in re.split(r"[^\w]+", A) if len(t) >= 5]
#     tb = [t for t in re.split(r"[^\w]+", B) if len(t) >= 5]
#     return bool(set(ta) & set(tb))

# def filter_drug_list(all_drug_names: List[str]) -> List[str]:
#     filtered = []
#     for name in all_drug_names:
#         if not name: 
#             continue
#         lower = name.lower().strip()
#         # Drop obviously useless single-word tokens
#         if len(lower) < 3:
#             continue
#         # Drop tokens that are purely common stop words or manufacturer fragments
#         if lower in STOP_WORDS:
#             continue
#         # your existing filters
#         if is_blacklisted(name):
#             continue
#         if len(name.split()) > 4:
#             continue
#         if any(x in lower for x in ["bayer", "brand", "compare to"]):
#             continue
#         filtered.append(name)
#     return filtered


# def best_drug_matches(
#     candidates: Set[str],
#     all_drug_names: List[str],
#     min_score: int = 85,
#     topk: int = 10,
#     _db_lower_to_orig: Dict[str, str] | None = None,
#     _db_keys: List[str] | None = None,
# ) -> List[Tuple[str, int]]:
#     if not candidates or not all_drug_names:
#         return []
#     if _db_lower_to_orig is None:
#         _db_lower_to_orig = {n.lower(): n for n in all_drug_names}
#     if _db_keys is None:
#         _db_keys = list(_db_lower_to_orig.keys())

#     matches: dict[str, float] = {}
#     for candidate in sorted(candidates, key=len, reverse=True):
#         best_db_key = None
#         best_score = -1.0
#         c_low = candidate.lower()

#         if c_low in _db_lower_to_orig:
#             best_db_key = c_low; best_score = 100.0
#         else:
#             result = process.extractOne(
#                 c_low, _db_keys, scorer=fuzz.token_sort_ratio, score_cutoff=min_score
#             )
#             if result:
#                 match_key, score = result[0], float(result[1])
#                 match_name_orig = _db_lower_to_orig[match_key]
#                 if reasonable_overlap(candidate, match_name_orig):
#                     best_db_key = match_key; best_score = score

#         if best_db_key:
#             db_name_orig = _db_lower_to_orig[best_db_key]
#             if db_name_orig not in matches or best_score > matches[db_name_orig]:
#                 matches[db_name_orig] = best_score

#     ranked = sorted(matches.items(), key=lambda x: (-x[1], -len(x[0])))
#     ranked = penalize_ingredients(ranked)
#     return ranked[:topk]

# # -----------------------------
# # Speed helpers (Unchanged)
# # -----------------------------
# def _resize_safe(bgr: np.ndarray) -> np.ndarray:
#     h, w = bgr.shape[:2]
#     if h > MAX_IMAGE_HEIGHT:
#         scale = MAX_IMAGE_HEIGHT / float(h)
#         return cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
#     return bgr

# def _phash_from_pil(pil_image: Image.Image) -> str:
#     arr = np.array(pil_image)
#     return "ocr:img:" + hashlib.sha1(arr.tobytes()).hexdigest()

# def _process_one_image(
#     image_file,
#     all_drug_names: List[str],
#     db_lower_to_orig: Dict[str, str],
#     db_keys: List[str],
# ) -> tuple[str | None, dict]:
#     image_file.seek(0)
#     pil_image = Image.open(image_file).convert("RGB")
#     cache_key = _phash_from_pil(pil_image)

#     cached = cache.get(cache_key)
#     if cached:
#         return cached["top_name"], cached["dbg"]

#     base_bgr = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
#     base_bgr = _resize_safe(base_bgr)

#     # Light pass
#     variants = generate_image_variants(base_bgr, light=True)
#     image_candidates: Set[str] = set()
#     best_variant_tokens: List[str] = []
#     raw_texts: List[str] = []
#     for variant in variants:
#         tokens, raw_text = ocr_tesseract(variant)
#         if len(tokens) > len(best_variant_tokens): best_variant_tokens = tokens
#         image_candidates |= make_candidates(raw_text, tokens)
#         if raw_text: raw_texts.append(raw_text)

#     matches = best_drug_matches(
#         image_candidates, all_drug_names, min_score=PER_IMAGE_MIN_SCORE, topk=5,
#         _db_lower_to_orig=db_lower_to_orig, _db_keys=db_keys
#     )
#      # --- Fallback: if no matches, try matching raw_text snippets with softer metrics ---
#     if not matches and raw_texts:
#         logging.info("[DEBUG] Strict matching returned no results — running raw_text fallback.")
#         fb_scores: Dict[str, float] = {}
#         # assemble candidate snippets to try (short list for speed)
#         raw_snips = []
#         for r in raw_texts:
#             # split into cleaned lines/phrases
#             for line in re.split(r"[\n\r;|/]+", r):
#                 s = re.sub(r"[^A-Za-z0-9\s]", " ", line).strip()
#                 if len(s) >= 3:
#                     raw_snips.append(s)
#         # try a few best unique snips
#         tried = 0
#         for sn in list(dict.fromkeys(raw_snips))[:40]:
#             tried += 1
#             # normalize and try partial and token_set scorers
#             key = sn.lower()
#             try:
#                 res1 = process.extractOne(key, db_keys, scorer=fuzz.token_set_ratio, score_cutoff=60)
#             except Exception:
#                 res1 = None
#             try:
#                 res2 = process.extractOne(key, db_keys, scorer=fuzz.partial_ratio, score_cutoff=60)
#             except Exception:
#                 res2 = None
#             for res in (res1, res2):
#                 if res:
#                     match_key = res[0] if isinstance(res[0], str) else res[0][0]
#                     score = float(res[1])
#                     name_orig = db_lower_to_orig.get(match_key)
#                     if name_orig:
#                         if name_orig not in fb_scores or score > fb_scores[name_orig]:
#                             fb_scores[name_orig] = score
#         if fb_scores:
#             ranked_fb = sorted(fb_scores.items(), key=lambda x: (-x[1], -len(x[0])))
#             logging.info(f"[DEBUG] Raw-text fallback ranked: {ranked_fb[:6]}")
#             matches = [(n, int(s)) for n, s in ranked_fb[:8]]
#     matches = keep_brands_first(matches, limit=5)
#     matches = [(n, s) for n, s in matches if not is_manufacturer(n)]

#     # --- THIS IS THE NEW ROBUST FIX ---
#     # We only exit early if the top match is a BRAND, not an ingredient
#     is_top_match_a_brand = is_brand_like(matches[0][0]) if matches else False
#     if (
#         matches and
#         matches[0][1] >= EARLY_EXIT_SCORE and
#         len(best_variant_tokens) >= MIN_TOKENS_FOR_CONFIDENCE and
#         is_top_match_a_brand  # <-- The new condition!
#     ):
#     # --- END OF FIX ---
#         dbg = {
#             "tokens_count": len(best_variant_tokens),
#             "candidates_count": len(image_candidates),
#             "matches": [{"name": m[0], "score": m[1]} for m in matches],
#             "early_exit": True,
#         }
#         top = matches[0][0]
#         cache.set(cache_key, {"top_name": top, "dbg": dbg}, timeout=CACHE_OCR_SECONDS)
#         return top, dbg

#     # One heavy rotation
#     more_variants = generate_image_variants(base_bgr, light=False)
#     if len(more_variants) > len(variants):
#         variant = more_variants[len(variants)]
#         tokens, raw_text = ocr_tesseract(variant)
#         if len(tokens) > len(best_variant_tokens): best_variant_tokens = tokens
#         image_candidates |= make_candidates(raw_text, tokens)
#         if raw_text: raw_texts.append(raw_text)

#     # Relaxed pass only if weak
#     if len(best_variant_tokens) < MIN_TOKENS_FOR_CONFIDENCE and not (matches and matches[0][1] >= 85):
#         r_tokens, r_raw = ocr_tesseract_relaxed(base_bgr)
#         if len(r_tokens) > len(best_variant_tokens): best_variant_tokens = r_tokens
#         image_candidates |= make_candidates(r_raw or "", r_tokens)
#         if r_raw: raw_texts.append(r_raw)

#     # --- ADDED DEBUG LOGGING ---
#     logging.info(f"[DEBUG] Candidates for this image: {image_candidates}")
    
#     matches = best_drug_matches(
#         image_candidates, all_drug_names, min_score=PER_IMAGE_MIN_SCORE, topk=5,
#         _db_lower_to_orig=db_lower_to_orig, _db_keys=db_keys
#     )
    
#     # --- ADDED DEBUG LOGGING ---
#     logging.info(f"[DEBUG] Top 5 matches for this image: {matches}")

#     matches = keep_brands_first(matches, limit=5)
#     matches = [(n, s) for n, s in matches if not is_manufacturer(n)]

#     dbg = {
#         "tokens_count": len(best_variant_tokens),
#         "candidates_count": len(image_candidates),
#         "matches": [{"name": m[0], "score": m[1]} for m in matches],
#         "early_exit": False,
#     }
#     top = matches[0][0] if matches else None
#     if top:
#         cache.set(cache_key, {"top_name": top, "dbg": dbg}, timeout=CACHE_OCR_SECONDS)
#     return top, dbg

# # -----------------------------
# # View
# # -----------------------------
# class ScanAndCheckView(APIView):
#     """
#     OCR-based drug/brand extraction (Tesseract-only, brand-first).
#     Uses local Interaction DB (DDInter import) for DDI.
#     """
#     parser_classes = (MultiPartParser, FormParser)

#     def post(self, request, *args, **kwargs):
#         image_files = request.FILES.getlist("images")
#         if not image_files:
#             return Response({"error": "No image files provided."}, status=400)

#         # --- THIS IS THE CORRECTED CACHE LOGIC ---
#         all_drug_names = cache.get("filtered_drug_names")
#         if not all_drug_names:
#             # 1. Get all global drug names
#             global_names = set(Drug.objects.values_list("name", flat=True))
            
#             # 2. Get all local Kenyan brand names
#             local_names = set(LocalBrand.objects.values_list("brand_name", flat=True))
            
#             # 3. Combine them into one list
#             combined_names_lower = {name.lower() for name in global_names}
#             combined_names_final = list(global_names)
            
#             for name in local_names:
#                 if name.lower() not in combined_names_lower:
#                     combined_names_final.append(name)
            
#             # 4. Filter the final list
#             all_drug_names = filter_drug_list(combined_names_final)
            
#             logging.info(f"Rebuilt drug name cache: {len(global_names)} global, {len(local_names)} local, {len(all_drug_names)} final unique names.")
            
#             cache.set("filtered_drug_names", all_drug_names, timeout=3600)
#         # --- END OF CACHE LOGIC FIX ---

#         db_lower_to_orig = {n.lower(): n for n in all_drug_names}
#         db_keys = list(db_lower_to_orig.keys())

#         logging.info("\n" + "=" * 60)
#         logging.info(f"[INFO] Processing {len(image_files)} images")
#         logging.info(f"[INFO] Searching against {len(all_drug_names)} pharmaceutical names")
#         logging.info("=" * 60 + "\n")

#         per_image_results: List[dict] = []
#         final_names: List[str] = []

#         # Parallel per-image (Unchanged)
#         with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
#             futures = [
#                 ex.submit(_process_one_image, f, all_drug_names, db_lower_to_orig, db_keys)
#                 for f in image_files
#             ]
#             for fut in as_completed(futures):
#                 try:
#                     top_name, dbg = fut.result()
#                     if top_name:
#                         final_names.append(top_name)
#                     per_image_results.append(dbg)
#                 except Exception as e:
#                     logging.error(f"[ERROR] Worker failed: {e}", exc_info=True)
#                     return Response({"error": "Server error processing an image."}, status=500)

#         # Dedup, cap (Unchanged)
#         seen = set(); ordered = []
#         for n in final_names:
#             if n not in seen:
#                 ordered.append(n); seen.add(n)
#         final_drug_names = ordered[:FINAL_MAX_RESULTS]

#         logging.info("\n" + "=" * 60)
#         if final_drug_names:
#             logging.info(f"[RESULT] Identified {len(final_drug_names)} drugs (Unique top picks per image):")
#             for n in final_drug_names:
#                 logging.info(f"  • {n}")
#         else:
#             logging.info("[RESULT] No drugs identified")
#         logging.info("=" * 60 + "\n")

#         if not final_drug_names:
#             return Response(
#                 {
#                     "error": "No known medication names were identified in the images.",
#                     "found_drug_names": [],
#                     "debug_info": {"per_image_results": per_image_results},
#                 },
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         # --- THIS CALLS THE CORRECT PAYLOAD FUNCTION ---
#         payload = self._pack_payload(final_drug_names)
#         payload["debug_info"] = {"per_image_results": per_image_results}

#         # Trim debug in production if you want (Unchanged)
#         if os.getenv("ENV") == "prod":
#             payload["debug_info"] = {"summary": {
#                 "images": len(image_files),
#                 "found": len(final_drug_names),
#             }}

#         return Response(payload, status=status.HTTP_200_OK)

#     # --- THIS IS THE CORRECTED PAYLOAD FUNCTION ---

#     def _generate_ai_summary(self, interactions: List[dict], drug_details: List[dict], found_drugs: List[str]) -> str:
#         """Robust HF summarizer with an internal truncation helper and multiple call attempts."""
#         if not SUMMARIZER_API:
#             return ""

#         def _truncate_prompt_local(text: str, max_chars: int = 2000) -> str:
#             if len(text) <= max_chars:
#                 return text
#             head = text[: max_chars // 2].rsplit(" ", 1)[0]
#             tail = text[-(max_chars // 2):].rsplit(" ", 1)[-1]
#             return head + "\n\n...TRUNCATED...\n\n" + tail

#         # Build the prompt/document
#         input_text = f"Report for a patient taking: {', '.join(found_drugs)}. "
#         if interactions:
#             input_text += "INTERACTIONS FOUND: "
#             for inter in interactions:
#                 input_text += f"- {inter.get('drug_1')} & {inter.get('drug_2')}: {inter.get('severity')}. {inter.get('description','No description')}. "
#         else:
#             input_text += "No interactions were found. "

#         input_text += "DRUG DETAILS: "
#         for detail in drug_details:
#             name = detail.get('name', 'Unknown')
#             info = detail.get('druginfo') or {}
#             if info:
#                 if info.get('side_effects'):
#                     input_text += f"{name}: {info.get('side_effects')}. "
#                 if info.get('warnings'):
#                     input_text += f"{name}: {info.get('warnings')}. "
#             else:
#                 input_text += f"{name}: No details available in database. "

#         prompt = (
#             "Summarize this technical report for a layperson. Start with the most important warning first. "
#             "Be friendly and clear: \"" + input_text + "\""
#         )

#         # Truncate to avoid tokenizer errors
#         prompt = _truncate_prompt_local(prompt, max_chars=2000)
#         logging.info(f"Calling Hugging Face AI for summary (prompt length: {len(prompt)} chars).")

#         # Candidate call attempts (some clients expose different methods/signatures)
#         def call_summarization_no_params():
#             return SUMMARIZER_API.summarization(prompt, model=AI_MODEL_NAME)

#         def call_text2text_gen_max_tokens():
#             return SUMMARIZER_API.text2text_generation(prompt, model=AI_MODEL_NAME, max_new_tokens=120)

#         def call_text_generation_max_tokens():
#             return SUMMARIZER_API.text_generation(prompt, model=AI_MODEL_NAME, max_new_tokens=120)

#         candidates = [call_summarization_no_params, call_text2text_gen_max_tokens, call_text_generation_max_tokens]

#         result = None
#         last_exc = None
#         for fn in candidates:
#             name = getattr(fn, "__name__", repr(fn))
#             try:
#                 logging.info(f"Attempting HF call style: {name}")
#                 result = fn()
#                 logging.info(f"HF call style {name} succeeded.")
#                 break
#             except BadRequestError as bre:
#                 logging.warning(f"BadRequest from HF using {name}: {bre!s}")
#                 last_exc = bre
#                 continue
#             except TypeError as te:
#                 logging.warning(f"TypeError calling HF with {name}: {te!s}")
#                 last_exc = te
#                 continue
#             except Exception as e:
#                 logging.warning(f"HF call with {name} failed: {e!s}")
#                 last_exc = e
#                 continue

#         if result is None:
#             logging.error(f"All Hugging Face call attempts failed. Last error: {last_exc!r}")
#             return "An error occurred while generating the AI summary. Please review the raw data below."

#         # Extract summary text from common return shapes
#         try:
#             summary_text = None
#             if hasattr(result, "generated_text"):
#                 summary_text = getattr(result, "generated_text")
#             elif isinstance(result, (list, tuple)) and len(result) > 0 and isinstance(result[0], dict):
#                 summary_text = result[0].get("summary_text") or result[0].get("generated_text")
#             elif isinstance(result, dict):
#                 summary_text = result.get("summary_text") or result.get("generated_text")
#                 if not summary_text and "generated_texts" in result and isinstance(result["generated_texts"], (list, tuple)):
#                     summary_text = result["generated_texts"][0] if result["generated_texts"] else None
#             else:
#                 summary_text = str(result)

#             if not summary_text:
#                 logging.error(f"Unexpected/empty HF result. Raw (truncated): {repr(result)[:2000]}")
#                 return "An error occurred while generating the AI summary. Please review the raw data below."

#             summary = summary_text.replace(" .", ".").strip()
#             logging.info("AI summary generated successfully.")
#             return summary

#         except Exception as e:
#             logging.error(f"Failed to parse HF result: {e}", exc_info=True)
#             logging.error(f"Raw HF result: {repr(result)[:2000]}")
#             return "An error occurred while parsing the AI summary. Please review the raw data below."


#     # --- FINAL VERSION: _pack_payload ---
#     def _pack_payload(self, drug_names: List[str]) -> dict:
#         """
#         Package drug information, interactions, AND the AI summary.
#         """
#         payload = {"found_drug_names": drug_names}
        
#         generic_names_to_check = set()
#         all_drug_objects_in_db = []
#         local_brand_stubs = [] 
        
#         for name in drug_names:
#             name_lower = name.lower()
            
#             try: # Check Drug table
#                 drug_obj = Drug.objects.get(name__iexact=name_lower)
#                 all_drug_objects_in_db.append(drug_obj)
#                 generic_names_to_check.add(drug_obj.name) 
#                 continue 
#             except Drug.DoesNotExist:
#                 pass 

#             try: # Check LocalBrand table
#                 local_brand_obj = LocalBrand.objects.get(brand_name__iexact=name_lower)
#                 ingredients = local_brand_obj.generic_names
#                 for ingredient in ingredients:
#                     generic_names_to_check.add(ingredient)
                
#                 ingredient_objs = Drug.objects.filter(name__in=ingredients)
#                 all_drug_objects_in_db.extend(list(ingredient_objs))
                
#                 logging.info(f"Mapped local brand '{name}' to ingredients: {ingredients}")

#                 # This is the "stub" text from before, which is good
#                 stub = {
#                     "name": name, 
#                     "druginfo": {
#                         "administration": "This is a local brand. Please check the product packaging for details.",
#                         "side_effects": f"Contains: {', '.join(ingredients)}. See ingredient details for more information.",
#                         "warnings": "This is a local brand. Please consult a healthcare professional for warnings."
#                     }
#                 }
#                 local_brand_stubs.append(stub)

#             except LocalBrand.DoesNotExist:
#                 logging.warning(f"'{name}' not found in Drug table or LocalBrand table. Skipping.")
        
#         # Get REAL drug details
#         unique_drug_objects = list({obj.id: obj for obj in all_drug_objects_in_db}.values())
#         serialized_drug_details = DrugSerializer(unique_drug_objects, many=True).data

#         payload["drug_details"] = serialized_drug_details + local_brand_stubs

#         # Get REAL interactions
#         local_interactions = []
#         final_ingredient_list = list(generic_names_to_check)
        
#         if len(final_ingredient_list) >= 2:
#             logging.info(f"Checking LOCAL DB for interactions among ingredients: {final_ingredient_list}")
#             local_interactions = Interaction.get_interactions(final_ingredient_list)
#         else:
#             logging.info("Less than 2 unique ingredients found, skipping interaction check.")

#         payload["interactions"] = local_interactions
        
#         # --- NEW: Call the AI Summarizer ---
#         # This is the final step that fulfills your proposal!
#         ai_summary = self._generate_ai_summary(
#             payload["interactions"],
#             payload["drug_details"],
#             payload["found_drug_names"]
#         )
#         payload["ai_summary"] = ai_summary
#         # --- END OF NEW STEP ---

#         return payload
# backend/drugs/views.py
from __future__ import annotations

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
# --- END NEW IMPORTS ---


logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(asctime)s:%(message)s")

# --- NEW: AI Summarizer Config ---
# (Your existing AI Summarizer config is unchanged)
AI_MODEL_NAME = "facebook/bart-large-cnn"
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
STOP_WORDS |= {"aspen", "care", "relief", "healthcare", "mara", "moja","rid"}

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

# ----------------------------------------------------
# --- END HELPER FUNCTION ---
# ----------------------------------------------------

# ... (Your ScanAndCheckView class) ...
class ScanAndCheckView(APIView):
    """
    OCR-based drug/brand extraction (Tesseract-only, brand-first).
    Uses local Interaction DB (DDInter import) for DDI.
    """
    
    # --- ADD THIS: Authentication settings ---
    # This will check for a token, but still allow anonymous users
    authentication_classes = [TokenAuthentication]
    permission_classes = [] 
    # --- END ADD ---

    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        image_files = request.FILES.getlist("images")
        if not image_files:
            return Response({"error": "No image files provided."}, status=400)

        # --- THIS IS THE CORRECTED CACHE LOGIC ---
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
            
            logging.info(f"Rebuilt drug name cache: {len(global_names)} global, {len(local_names)} local, {len(all_drug_names)} final unique names.")
            
            cache.set("filtered_drug_names", all_drug_names, timeout=3600)
        # --- END OF CACHE LOGIC FIX ---

        db_lower_to_orig = {n.lower(): n for n in all_drug_names}
        db_keys = list(db_lower_to_orig.keys())

        logging.info("\n" + "=" * 60)
        logging.info(f"[INFO] Processing {len(image_files)} images")
        logging.info(f"[INFO] Searching against {len(all_drug_names)} pharmaceutical names")
        logging.info("=" * 60 + "\n")

        per_image_results: List[dict] = []
        final_names: List[str] = []

        # Parallel per-image (Unchanged)
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

        # Dedup, cap (Unchanged)
        seen = set(); ordered = []
        for n in final_names:
            if n not in seen:
                ordered.append(n); seen.add(n)
        final_drug_names = ordered[:FINAL_MAX_RESULTS]

        logging.info("\n" + "=" * 60)
        if final_drug_names:
            logging.info(f"[RESULT] Identified {len(final_drug_names)} drugs (Unique top picks per image):")
            for n in final_drug_names:
                logging.info(f"   • {n}")
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

        # --- THIS CALLS THE CORRECT PAYLOAD FUNCTION ---
        payload = self._pack_payload(final_drug_names)
        payload["debug_info"] = {"per_image_results": per_image_results}

        # --- ADD THIS: Save scan to history if user is logged in ---
        if request.user.is_authenticated:
            try:
                ScanHistory.objects.create(
                    user=request.user,
                    drug_names=final_drug_names,
                    scan_results=payload  # Save the entire report
                )
                logging.info(f"Scan history saved for user: {request.user.username}")
            except Exception as e:
                # We don't want to fail the whole request if history fails
                logging.error(f"Failed to save scan history for user {request.user.username}: {e}")
        # --- END ADD ---


        # Trim debug in production if you want (Unchanged)
        if os.getenv("ENV") == "prod":
            payload["debug_info"] = {"summary": {
                "images": len(image_files),
                "found": len(final_drug_names),
            }}

        return Response(payload, status=status.HTTP_200_OK)

    # --- THIS IS THE CORRECTED PAYLOAD FUNCTION ---

    def _generate_ai_summary(self, interactions: List[dict], drug_details: List[dict], found_drugs: List[str], user=None) -> str:
            """
            Robust HF summarizer.
            UPGRADE: Now checks for user allergies/conditions if the user is logged in.
            """
            if not SUMMARIZER_API:
                return ""

            def _truncate_prompt_local(text: str, max_chars: int = 2000) -> str:
                if len(text) <= max_chars:
                    return text
                head = text[: max_chars // 2].rsplit(" ", 1)[0]
                tail = text[-(max_chars // 2):].rsplit(" ", 1)[-1]
                return head + "\n\n...TRUNCATED...\n\n" + tail

            # --- 1. NEW: Get Patient Context (The "Killer Feature") ---
            patient_context = ""
            if user and user.is_authenticated:
                try:
                    # Safely access profile (using getattr to avoid crashes if profile missing)
                    profile = getattr(user, 'profile', None)
                    if profile:
                        # Format the list into a string string like "Peanuts, Penicillin"
                        allergies = ", ".join(profile.allergies) if profile.allergies else "None"
                        conditions = ", ".join(profile.conditions) if profile.conditions else "None"
                        patient_context = f"\nPATIENT CONTEXT:\n- User's Allergies: {allergies}\n- User's Medical Conditions: {conditions}\n"
                except Exception as e:
                    logging.warning(f"Could not fetch profile for summary: {e}")
            # ----------------------------------------------------------

            # --- 2. ORIGINAL: Build the Report ---
            # We start with your original report structure
            input_text = f"Report for a patient taking: {', '.join(found_drugs)}. "
            
            # Inject the new context right at the start
            input_text += patient_context

            if interactions:
                input_text += "INTERACTIONS FOUND: "
                for inter in interactions:
                    input_text += f"- {inter.get('drug_1')} & {inter.get('drug_2')}: {inter.get('severity')}. {inter.get('description','No description')}. "
            else:
                input_text += "No interactions were found. "

            input_text += "DRUG DETAILS: "
            for detail in drug_details:
                name = detail.get('name', 'Unknown')
                info = detail.get('druginfo') or {}
                if info:
                    if info.get('side_effects'):
                        input_text += f"{name}: {info.get('side_effects')}. "
                    if info.get('warnings'):
                        input_text += f"{name}: {info.get('warnings')}. "
                else:
                    input_text += f"{name}: No details available in database. "

            # --- 3. UPDATED: The Prompt ---
            # This prompt keeps your "friendly" requirement but adds the safety check.
            prompt = (
                "You are a medical safety assistant. Summarize this report for a layperson. "
                "Be friendly and clear.\n"
                "CRITICAL: Check the 'PATIENT CONTEXT' against the drugs. "
                "If the user has an allergy or condition that conflicts with these drugs, WARN THEM FIRST.\n"
                "Then, summarize the interactions and side effects.\n\n"
                f"Report Data:\n\"{input_text}\""
            )

            # Truncate to avoid tokenizer errors (Safe limit increased slightly to 3000)
            prompt = _truncate_prompt_local(prompt, max_chars=3000)
            logging.info(f"Calling Hugging Face AI for summary (prompt length: {len(prompt)} chars).")

            # --- 4. ORIGINAL: The API Calls (Unchanged) ---
            def call_summarization_no_params():
                return SUMMARIZER_API.summarization(prompt, model=AI_MODEL_NAME)

            def call_text2text_gen_max_tokens():
                return SUMMARIZER_API.text2text_generation(prompt, model=AI_MODEL_NAME, max_new_tokens=120)

            def call_text_generation_max_tokens():
                return SUMMARIZER_API.text_generation(prompt, model=AI_MODEL_NAME, max_new_tokens=120)

            candidates = [call_summarization_no_params, call_text2text_gen_max_tokens, call_text_generation_max_tokens]

            result = None
            last_exc = None
            for fn in candidates:
                name = getattr(fn, "__name__", repr(fn))
                try:
                    logging.info(f"Attempting HF call style: {name}")
                    result = fn()
                    logging.info(f"HF call style {name} succeeded.")
                    break
                except Exception as e:
                    logging.warning(f"HF call with {name} failed: {e!s}")
                    last_exc = e
                    continue

            if result is None:
                logging.error(f"All Hugging Face call attempts failed. Last error: {last_exc!r}")
                return "An error occurred while generating the AI summary."

            # Extract result (Unchanged logic)
            try:
                summary_text = None
                if hasattr(result, "generated_text"):
                    summary_text = getattr(result, "generated_text")
                elif isinstance(result, (list, tuple)) and len(result) > 0 and isinstance(result[0], dict):
                    summary_text = result[0].get("summary_text") or result[0].get("generated_text")
                elif isinstance(result, dict):
                    summary_text = result.get("summary_text") or result.get("generated_text")
                    if not summary_text and "generated_texts" in result:
                        summary_text = result["generated_texts"][0] if result["generated_texts"] else None
                else:
                    summary_text = str(result)

                if not summary_text:
                    return "An error occurred while generating the AI summary."

                summary = summary_text.replace(" .", ".").strip()
                logging.info("AI summary generated successfully.")
                return summary

            except Exception as e:
                logging.error(f"Failed to parse HF result: {e}", exc_info=True)
                return "An error occurred while parsing the AI summary."
    # --- FINAL VERSION: _pack_payload ---
    def _pack_payload(self, drug_names: List[str]) -> dict:
        """
        Package drug information, interactions, AND the AI summary.
        """
        payload = {"found_drug_names": drug_names}
        
        generic_names_to_check = set()
        all_drug_objects_in_db = []
        local_brand_stubs = [] 
        
        for name in drug_names:
            name_lower = name.lower()
            
            try: # Check Drug table
                drug_obj = Drug.objects.get(name__iexact=name_lower)
                all_drug_objects_in_db.append(drug_obj)
                generic_names_to_check.add(drug_obj.name) 
                continue 
            except Drug.DoesNotExist:
                pass 

            try: # Check LocalBrand table
                local_brand_obj = LocalBrand.objects.get(brand_name__iexact=name_lower)
                ingredients = local_brand_obj.generic_names
                for ingredient in ingredients:
                    generic_names_to_check.add(ingredient)
                
                ingredient_objs = Drug.objects.filter(name__in=ingredients)
                all_drug_objects_in_db.extend(list(ingredient_objs))
                
                logging.info(f"Mapped local brand '{name}' to ingredients: {ingredients}")

                # This is the "stub" text from before, which is good
                stub = {
                    "name": name, 
                    "druginfo": {
                        "administration": "This is a local brand. Please check the product packaging for details.",
                        "side_effects": f"Contains: {', '.join(ingredients)}. See ingredient details for more information.",
                        "warnings": "This is a local brand. Please consult a healthcare professional for warnings."
                    }
                }
                local_brand_stubs.append(stub)

            except LocalBrand.DoesNotExist:
                logging.warning(f"'{name}' not found in Drug table or LocalBrand table. Skipping.")
        
        # Get REAL drug details
        unique_drug_objects = list({obj.id: obj for obj in all_drug_objects_in_db}.values())
        
        # --- THIS NOW USES YOUR SERIALIZER ---
        # It will automatically find and nest the 'druginfo' data
        # because you created 'serializers.py'
        serialized_drug_details = DrugSerializer(unique_drug_objects, many=True).data

        payload["drug_details"] = serialized_drug_details + local_brand_stubs

        # Get REAL interactions
        local_interactions = []
        final_ingredient_list = list(generic_names_to_check)
        
        if len(final_ingredient_list) >= 2:
            logging.info(f"Checking LOCAL DB for interactions among ingredients: {final_ingredient_list}")
            local_interactions = Interaction.get_interactions(final_ingredient_list)
        else:
            logging.info("Less than 2 unique ingredients found, skipping interaction check.")

        payload["interactions"] = local_interactions
        
        # --- NEW: Call the AI Summarizer ---
        # This is the final step that fulfills your proposal!
        ai_summary = self._generate_ai_summary(
            payload["interactions"],
            payload["drug_details"],
            payload["found_drug_names"],
            user=request.user
        )
        payload["ai_summary"] = ai_summary
        # --- END OF NEW STEP ---

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

class LoginView(APIView):
    """
    API view for user login.
    UPGRADED: Now handles 2FA.
    """
    permission_classes = [] 
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        otp_code = request.data.get('otp_code') # <-- Check if user sent a code

        if not username or not password:
            return Response({"error": "Please provide username and password"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            # 1. Check if user has an active 2FA device
            # We assume confirmed=True means setup is complete
            device = TOTPDevice.objects.filter(user=user, confirmed=True).first()

            if device:
                # 2. User has 2FA enabled. Did they send a code?
                if not otp_code:
                    # Tell frontend: "Password good, but I need a code"
                    return Response(
                        {"requires_2fa": True, "message": "2FA code required"}, 
                        status=status.HTTP_200_OK
                    )
                
                # 3. Verify the code
                if not device.verify_token(otp_code):
                    return Response(
                        {"error": "Invalid 2FA code"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # 4. Login successful (either no 2FA or code was valid)
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key, 
                "username": user.username,
                "requires_2fa": False
            }, status=status.HTTP_200_OK)
            
        else:
            return Response({"error": "Invalid username or password"}, status=status.HTTP_401_UNAUTHORIZED)


class Setup2FAView(APIView):
    """
    Generates a QR code for the user to scan with Google Authenticator.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Get or create a device. 'confirmed=False' until they verify a code.
        device, created = TOTPDevice.objects.get_or_create(user=user, name="default")
        
        # Generate the provisioning URL (the data inside the QR code)
        url = device.config_url
        
        # Create QR code image in memory
        img = qrcode.make(url)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return Response({
            "qr_code": f"data:image/png;base64,{img_str}",
            "secret_key": device.key  # Sometimes useful to show manual entry key
        })

class Verify2FAView(APIView):
    """
    Finalizes 2FA setup. User sends a code to prove they scanned the QR.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get('code')
        user = request.user
        
        # Find the unconfirmed device
        device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
        
        if not device:
            # Maybe they already confirmed it?
            if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
                return Response({"message": "2FA is already enabled."}, status=status.HTTP_200_OK)
            return Response({"error": "No pending 2FA setup found."}, status=status.HTTP_400_BAD_REQUEST)

        # Verify the code
        if device.verify_token(code):
            device.confirmed = True
            device.save()
            return Response({"message": "2FA enabled successfully!"}, status=status.HTTP_200_OK)
        else:
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
    parser_classes = (MultiPartParser, FormParser,JSONParser) # <-- ADD THIS for image uploads

    def get(self, request):
        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)
        scan_count = ScanHistory.objects.filter(user=user).count()
        
        # Use the serializer to format the profile data (including avatar)
        profile_data = ProfileSerializer(profile).data
        
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
        
        # partial=True allows us to update just the avatar without sending allergies
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
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