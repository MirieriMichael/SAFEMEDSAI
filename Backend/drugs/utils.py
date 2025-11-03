# backend/drugs/utils.py
import requests
import json
import logging
from typing import List, Dict, Optional, Any
from django.core.cache import cache

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(asctime)s:%(message)s')

# --- API Configuration ---
RXNAV_API_BASE = "https://rxnav.nlm.nih.gov/REST"

# This header is to make our requests look like a browser
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36',
    'Accept': 'application/json'
}
# --- End Configuration ---


def get_rxcui_from_name(drug_name: str) -> Optional[str]:
    """
    Get the RxCUI (concept ID) from a drug name.
    We still use this to populate our Drug model.
    """
    if not drug_name:
        return None

    cache_key = f"rxcui_for_{drug_name.lower().strip()}"
    cached_rxcui = cache.get(cache_key)

    if cached_rxcui:
        logging.debug(f"Cache HIT for RxCUI: {drug_name} -> {cached_rxcui}")
        return None if cached_rxcui == "NOT_FOUND" else cached_rxcui

    logging.debug(f"Cache MISS for RxCUI: {drug_name}")
    try:
        url = f"{RXNAV_API_BASE}/approximateTerm.json?term={drug_name.lower()}&maxEntries=1"
        response = requests.get(url, timeout=10, headers=REQUEST_HEADERS)
        response.raise_for_status()
        data = response.json()

        group = data.get('approximateGroup')
        if group and group.get('candidate'):
            rxcui = group['candidate'][0].get('rxcui')
            if rxcui:
                logging.info(f"Found RxCUI {rxcui} for name '{drug_name}'")
                cache.set(cache_key, str(rxcui), timeout=3600 * 24) 
                return str(rxcui)

        logging.warning(f"RxCUI not found via approximateTerm for '{drug_name}'")
        cache.set(cache_key, "NOT_FOUND", timeout=3600)
        return None

    except requests.exceptions.RequestException as e:
        logging.error(f"API error getting RxCUI for '{drug_name}': {e}")
        return None
    except Exception as e:
         logging.error(f"Unexpected error in get_rxcui_from_name: {e}", exc_info=True)
         return None

#
# --- NO MORE API CALLS FOR INTERACTIONS ---
# All other functions (get_ndc_from_rxcui, get_interactions_from_ndcs, etc.)
# are no longer needed because the logic is now in models.py (Interaction.get_interactions)
#