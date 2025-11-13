# backend/drugs/hf_summarizer.py
import os
import json
import logging
import re
from typing import Dict, Any, Optional
from huggingface_hub import InferenceClient, HfApi

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

HF_MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.2"
HF_TOKEN = os.getenv("HF_TOKEN")

try:
    if not HF_TOKEN:
        logger.warning("[hf_summarizer] HF_TOKEN not set. AI calls will fail.")
        client = None
    else:
        client = InferenceClient(api_key=HF_TOKEN) 
        logger.info(f"InferenceClient initialized. Ready to call providers.")
except Exception as e:
    logger.error(f"[hf_summarizer] Failed to initialize InferenceClient: {e}")
    client = None


def _extract_json_like(text: str) -> Optional[str]:
    """Finds the first complete JSON object in a string."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, min(len(text), start + 20000)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    logger.warning(f"Could not extract complete JSON from text: {text[:200]}...")
    return None

def parse_ai_field(field_data: Any) -> str:
    """
    Handles the AI's output, whether it's a string,
    a list of strings, or None.
    """
    if not field_data:
        return ""
    
    if isinstance(field_data, list):
        # If it's a list (like ["Nausea", "Vomiting"]), join it
        return ", ".join(field_data)
        
    if isinstance(field_data, str):
        # If it's a plain string, just strip it
        return field_data.strip()
        
    # Fallback for other types
    return str(field_data)


def summarize_structured(source_text: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Handles BOTH summarizing and generating.
    - If source_text is large, it summarizes.
    - If source_text starts with "GENERATE_DATA_FOR:", it generates.
    """
    if not client:
        logger.warning("[hf_summarizer] Client not initialized. Skipping AI call.")
        return {"debug": "HF_CLIENT_not_initialized"}

    if not source_text:
        logger.warning("[hf_summarizer] source text is empty; skipping HF call.")
        return {"debug": "source_text_empty"}

    prompt = ""
    
    # --- THIS IS THE NEW LOGIC ---
    if source_text.startswith("GENERATE_DATA_FOR:"):
        # --- GENERATE MODE ---
        drug_name = source_text.replace("GENERATE_DATA_FOR:", "").strip()
        logger.info(f"Building GENERATOR prompt for: {drug_name}")
        prompt = f"""[INST] You are a helpful clinical assistant. A user needs simple, layperson-friendly data for the drug "{drug_name}".
Generate a JSON object with these keys:
- "overview": A one-sentence summary of what this drug is for.
- "side_effects": A simple list of 3-5 common side effects (e.g., "Nausea, Vomiting, Diarrhea").
- "interactions": A short summary of 1-2 important interactions (e.g., "Avoid alcohol").
- "administration": Simple instructions on how to take it (e.g., "Take one tablet daily as directed by your doctor").

Return ONLY the JSON object.
[/INST]"""
    
    else:
        # --- SUMMARIZE MODE ---
        logger.info(f"Building SUMMARIZER prompt...")
        truncated_source = source_text[:3500]
        prompt = f"""[INST] You are a helpful clinical summarization assistant.
Extract key information from the source text and return ONLY a single JSON object.
The JSON must have these keys:
- "overview" (a one-sentence summary)
- "side_effects" (a simple list for a layperson, e.g., "Nausea, Vomiting, Diarrhea")
- "interactions" (a short summary of 2-3 important interactions)
- "administration" (simple instructions on how to take it, e.g., "Take one tablet daily")

Do NOT use technical jargon. If data for a key is not found, return an empty string "" for that key.

Source Text:
{truncated_source}
[/INST]"""
    # --- END OF NEW LOGIC ---

    try:
        logger.info(f"Calling {HF_MODEL_ID} via Auto-Routing...")
        messages = [{"role": "user", "content": prompt}]
        
        completion = client.chat.completions.create(
            model=HF_MODEL_ID,
            messages=messages,
            max_tokens=512,
            temperature=0.1,
        )

        text_out = completion.choices[0].message.content
        if not text_out:
            logger.warning("AI returned an empty response.")
            return {"debug": "ai_returned_empty_response"}

        logger.info(f"Raw AI Output: {text_out}")
        json_str = _extract_json_like(text_out)
        
        if not json_str:
            logger.warning("AI did not return a parsable JSON.")
            return {"debug": f"ai_did_not_return_json: {text_out[:200]}"}

        try:
            parsed_data = json.loads(json_str)
            
            return {
                "overview": parse_ai_field(parsed_data.get("overview")),
                "side_effects": parse_ai_field(parsed_data.get("side_effects")),
                "interactions": parse_ai_field(parsed_data.get("interactions")),
                "administration": parse_ai_field(parsed_data.get("administration")),
                "debug": "parsed_structured_json",
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from AI: {e}\nText was: {json_str}")
            return {"debug": f"json_decode_error: {e}"}

    except Exception as e:
        logger.error(f"[hf_summarizer] API call error: {e}")
        return {"debug": f"hf_api_call_error:{e}"}