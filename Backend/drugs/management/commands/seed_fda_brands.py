# backend/drugs/management/commands/seed_fda_brands.py
import requests
import time
import string
from django.core.management.base import BaseCommand
from django.db import transaction
from drugs.models import Drug
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(asctime)s:%(message)s')

# --- Configuration ---
API_URL = 'https://api.fda.gov/drug/label.json'
LIMIT_PER_QUERY = 1000 # Max allowed by OpenFDA
MAX_RESULTS_PER_LETTER = 5000 # Limit how many results to process per starting letter
# ---------------------

class Command(BaseCommand):
    help = 'Adds Brand Names from OpenFDA drug labels to the Drug table.'

    def handle(self, *args, **options):
        logging.info("Starting import of Brand Names from OpenFDA...")

        # Get existing names to avoid duplicates (case-insensitive check)
        existing_names_lower = set(name.lower() for name in Drug.objects.values_list('name', flat=True))
        logging.info(f"Loaded {len(existing_names_lower)} existing drug names (lowercase).")

        total_added_count = 0
        processed_brands = set() # Track brands processed in this run to avoid duplicates within run

        # Iterate through letters A-Z to get broader coverage
        for letter in string.ascii_uppercase:
            logging.info(f"--- Querying for brands starting with '{letter}' ---")
            skip = 0
            added_for_letter = 0
            retrieved_for_letter = 0

            while retrieved_for_letter < MAX_RESULTS_PER_LETTER:
                # Query for labels where brand_name starts with the letter
                params = {
                    'search': f'openfda.brand_name:{letter}*',
                    'limit': LIMIT_PER_QUERY,
                    'skip': skip
                }
                logging.info(f"Querying API with skip={skip}...")

                try:
                    response = requests.get(API_URL, params=params, timeout=30) # Add timeout
                    response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

                    data = response.json()
                    results = data.get('results', [])
                    if not results:
                        logging.info(f"No more results found for letter '{letter}' starting at skip={skip}.")
                        break # No more results for this letter

                    retrieved_count = len(results)
                    retrieved_for_letter += retrieved_count
                    logging.info(f"Retrieved {retrieved_count} labels (Total for '{letter}': {retrieved_for_letter}).")

                    batch_to_create = []
                    for item in results:
                        brand_names = item.get('openfda', {}).get('brand_name', [])
                        for brand_name in brand_names:
                             # Basic cleaning: strip whitespace, remove common suffixes if desired
                             cleaned_name = brand_name.strip().split('(')[0].strip() # Remove '(..)' parts
                             cleaned_name_lower = cleaned_name.lower()

                             # Check length, stop words (optional but good), and if already processed/exists
                             if (cleaned_name_lower and len(cleaned_name_lower) > 2 and
                                 cleaned_name_lower not in existing_names_lower and
                                 cleaned_name_lower not in processed_brands and
                                 cleaned_name_lower not in ['drug']): # Add simple stop words

                                 batch_to_create.append(Drug(name=cleaned_name))
                                 processed_brands.add(cleaned_name_lower) # Track processed in this run

                    if batch_to_create:
                        try:
                            with transaction.atomic():
                                Drug.objects.bulk_create(batch_to_create, ignore_conflicts=True)
                                added_count = len(batch_to_create)
                                added_for_letter += added_count
                                total_added_count += added_count
                                logging.info(f"Added batch of {added_count} new brands for letter '{letter}'.")
                        except Exception as db_exc:
                             logging.error(f"Database error saving batch for letter '{letter}': {db_exc}")

                    skip += LIMIT_PER_QUERY
                    time.sleep(0.1) # Be polite to the API

                except requests.exceptions.RequestException as e:
                    logging.error(f"API request failed for letter '{letter}' (skip={skip}): {e}")
                    time.sleep(5) # Wait longer after an error before retrying or moving on
                    # Optionally add retry logic here
                    break # Stop processing this letter on error for simplicity

            logging.info(f"Finished processing letter '{letter}'. Added {added_for_letter} new brands.")

        logging.info(f"Finished adding brand names from OpenFDA. Total added in this run: {total_added_count}")