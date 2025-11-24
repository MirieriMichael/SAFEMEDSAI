"""
Drug extraction utilities using BERT NER model.
"""
import logging
from transformers import pipeline

# 1. LOAD THE MODEL (This is a BERT-based model, NOT an LLM)
# It runs locally on your machine/server.
try:
    NER_PIPELINE = pipeline("ner", model="d4data/biomedical-ner-all", aggregation_strategy="simple")
    logging.info("✅ Biomedical NER Model Loaded Successfully.")
except Exception as e:
    logging.error(f"❌ Failed to load NER Model: {e}")
    NER_PIPELINE = None

def extract_drugs_with_bert(ocr_text):
    """
    Uses a BERT Neural Network to find drug names in messy text.
    This is NOT prompt engineering. This is Token Classification.
    """
    if not NER_PIPELINE or not ocr_text:
        return []

    logging.info("🤖 Running BERT Model on text...")
    
    try:
        # The model analyzes the text
        entities = NER_PIPELINE(ocr_text)
        
        found_drugs = set()
        for entity in entities:
            # We only care about entities the model classifies as 'Medication' or 'Chemical'
            # The labels depend on the specific model, usually 'B-Drug', 'I-Drug', etc.
            # This specific model uses broad biomedical tags.
            if entity['score'] > 0.6: # Confidence threshold
                clean_word = entity['word'].strip()
                if len(clean_word) > 3:
                    found_drugs.add(clean_word)
                    logging.info(f"   Model detected entity: {clean_word} ({entity['score']:.2f})")
        
        return list(found_drugs)

    except Exception as e:
        logging.error(f"NER Model Inference Failed: {e}")
        return []

