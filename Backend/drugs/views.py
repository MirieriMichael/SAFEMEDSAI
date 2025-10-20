# backend/drugs/views.py
import pytesseract
from PIL import Image
import cv2
import numpy as np
from rapidfuzz import process, fuzz
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Drug, Interaction
from .serializers import InteractionSerializer, DrugSerializer
from itertools import combinations
from django.db.models import Q
from django.core.cache import cache
import platform

# --- Final Tesseract Configuration ---
if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    tessdata_dir_config = r'--tessdata-dir "C:\Program Files\Tesseract-OCR\tessdata"'
else:
    tessdata_dir_config = r''

# This is the final, most reliable configuration confirmed by our tests.
# PSM 6 assumes a single uniform block of text, which is perfect for a label.
OCR_CONFIG = f'{tessdata_dir_config} --oem 3 --psm 6'
# ------------------------------------

def deskew_advanced(image):
    """
    Deskews an image by detecting lines using the Hough Line Transform.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=50, maxLineGap=20)
    if lines is None:
        return image # Return original if no lines are found
    angles = [np.rad2deg(np.arctan2(y2 - y1, x2 - x1)) for line in lines for x1, y1, x2, y2 in [line[0]]]
    if not angles:
        return image # Return original if no angles are found
    median_angle = np.median(angles)
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

class InteractionCheckView(APIView):
    # This class remains unchanged
    def post(self, request, *args, **kwargs):
        drug_names = request.data.get('drugs', [])
        if not drug_names or len(drug_names) < 2:
            return Response({"error": "Please provide at least two drug names."}, status=status.HTTP_400_BAD_REQUEST)
        response_data = self.get_interaction_data(drug_names)
        return Response(response_data, status=status.HTTP_200_OK)

    def get_interaction_data(self, drug_names):
        drugs_in_query = Drug.objects.filter(name__in=drug_names).prefetch_related('druginfo')
        drug_pairs = list(combinations(drugs_in_query, 2))
        found_interactions = []
        for pair in drug_pairs:
            interaction = Interaction.objects.filter(
                (Q(drug_a=pair[0]) & Q(drug_b=pair[1])) |
                (Q(drug_a=pair[1]) & Q(drug_b=pair[0]))
            ).first()
            if interaction:
                found_interactions.append(interaction)
        drug_details_serializer = DrugSerializer(drugs_in_query, many=True)
        interaction_serializer = InteractionSerializer(found_interactions, many=True)
        return {
            'interactions': interaction_serializer.data,
            'drug_details': drug_details_serializer.data
        }

class ScanAndCheckView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        image_files = request.FILES.getlist('images')
        if not image_files:
            return Response({"error": "No image files provided."}, status=status.HTTP_400_BAD_REQUEST)

        full_text = ""
        for image_file in image_files:
            try:
                # Convert the uploaded file to an OpenCV image in memory
                image = Image.open(image_file).convert('RGB')
                opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

                # --- Use our final, robust processing pipeline ---
                # 1. Straighten the image
                deskewed_image = deskew_advanced(opencv_image)
                
                # 2. Convert to grayscale (the best method we found)
                final_image = cv2.cvtColor(deskewed_image, cv2.COLOR_BGR2GRAY)

                # 3. Feed the clean, straight, grayscale image to Tesseract
                extracted_text = pytesseract.image_to_string(final_image, lang='eng', config=OCR_CONFIG)
                if extracted_text.strip():
                    full_text += " " + extracted_text.strip()

            except Exception as e:
                print(f"ERROR DURING OCR: {e}")
                return Response({"error": "A server-side error occurred during image processing."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not full_text.strip():
            return Response({"error": "Could not detect any text in the uploaded images."}, status=status.HTTP_400_BAD_REQUEST)

        # Fuzzy matching will correct the minor OCR errors
        all_drug_names = cache.get('all_drug_names')
        if not all_drug_names:
            all_drug_names = list(Drug.objects.values_list('name', flat=True))
            cache.set('all_drug_names', all_drug_names, timeout=3600)

        words_from_ocr = set(full_text.replace('\n', ' ').split(' '))
        found_drugs = set()
        for word in words_from_ocr:
            if len(word) > 3:
                # Use a slightly lower cutoff to catch minor misspellings like 'Ibuprorerr'
                best_match = process.extractOne(word, all_drug_names, scorer=fuzz.partial_ratio, score_cutoff=85)
                if best_match:
                    found_drugs.add(best_match[0])

        if len(found_drugs) < 2:
            detected = ', '.join(found_drugs) if found_drugs else 'None'
            return Response(
                {"error": f"Found fewer than two known medications in the text. Detected: {detected}. Raw OCR text: '{full_text}'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        interaction_checker = InteractionCheckView()
        final_list_of_drugs = list(found_drugs)
        response_data = interaction_checker.get_interaction_data(final_list_of_drugs)
        response_data['found_drugs'] = final_list_of_drugs

        return Response(response_data, status=status.HTTP_200_OK)