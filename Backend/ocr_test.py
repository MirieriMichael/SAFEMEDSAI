# ocr_test.py
import pytesseract
from PIL import Image
import cv2
import numpy as np
import platform
import os

print("--- Starting Exhaustive OCR Tuning Test ---")

def deskew_advanced(image):
    # This advanced deskew function is working correctly.
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=50, maxLineGap=20)
    if lines is None:
        print("Warning: No lines detected for deskewing. Using original image.")
        return image
    angles = [np.rad2deg(np.arctan2(y2 - y1, x2 - x1)) for line in lines for x1, y1, x2, y2 in [line[0]]]
    if not angles:
        print("Warning: Could not determine angles. Using original image.")
        return image
    median_angle = np.median(angles)
    print(f"Deskewing complete. Detected median angle: {median_angle:.2f} degrees.")
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

# --- Configuration ---
try:
    if platform.system() == "Windows":
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        tessdata_dir_config = r'--tessdata-dir "C:\Program Files\Tesseract-OCR\tessdata"'
    else:
        tessdata_dir_config = ''
    print("Base configuration is OK.")
except Exception as e:
    print(f"An error occurred during configuration: {e}")
    exit()

# --- Image Processing and Systematic OCR ---
try:
    image_filename = 'Bru.jpg' 
    if not os.path.exists(image_filename):
        print(f"ERROR: Image file '{image_filename}' not found.")
        exit()
    
    original_image = cv2.imread(image_filename)
    deskewed_image = deskew_advanced(original_image)
    gray = cv2.cvtColor(deskewed_image, cv2.COLOR_BGR2GRAY)
    
    # --- Create a dictionary of different image processing methods ---
    processed_images = {
        "Grayscale Only": gray,
        "Otsu Threshold": cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        "Otsu Inverted": cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    }
    
    # --- Systematically test the most effective configurations ---
    psm_modes_to_test = ['3', '6', '7', '11']
    
    for method_name, image_to_test in processed_images.items():
        print(f"\n=======================================================")
        print(f"// TESTING IMAGE METHOD: {method_name} //")
        print(f"=======================================================")
        
        # Save the image being tested so we can see it
        cv2.imwrite(f'test_image_{method_name.replace(" ", "_")}.png', image_to_test)
        
        for psm in psm_modes_to_test:
            ocr_config = f'{tessdata_dir_config} --oem 3 --psm {psm}'
            
            print(f"\n--- Running with PSM {psm} ---")
            try:
                text = pytesseract.image_to_string(image_to_test, lang='eng', config=ocr_config)
                print("Result:")
                print("--------------------")
                print(text.strip() or "FAILURE: No text detected.")
                print("--------------------")
            except Exception as e:
                print(f"ERROR: Tesseract crashed with this configuration. {e}")

except Exception as e:
    print(f"A fatal error occurred: {e}")
    exit()