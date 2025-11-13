# # backend/drugs/management/commands/seed_druginfo.py
# import os
# import time
# import logging
# import traceback
# from typing import Optional, Tuple

# import requests
# from django.core.management.base import BaseCommand
# from django.db.models import Q

# from drugs.models import Drug, DrugInfo
# from drugs.hf_summarizer import summarize_structured

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)

# # --- THIS IS THE FIX ---
# # This is our NEW "permanent" fallback text.
# # The script will save this when a drug fails.
# PERMANENT_FALLBACK = "Data not available in public databases."

# # This is our "To-Do list" of all text that
# # needs to be processed.
# BAD_DATA_STRINGS = [
#     "ADVERSE REACTIONS",
#     "WARNINGS AND PRECAUTIONS",
#     "No information available",
#     "No side-effect details available",
#     "No warning details available",
#     "No administration details",
#     # We add the new fallback text to this list ONLY for the 'generation'
#     # so that if the AI fails, we don't try again.
#     PERMANENT_FALLBACK 
# ]
# # --- END OF FIX ---


# class Command(BaseCommand):
#     help = 'Populates the DrugInfo table using a hybrid OpenFDA + HF-API approach.'

#     def add_arguments(self, parser):
#         parser.add_argument(
#             '--batch_size', 
#             type=int, 
#             default=50, 
#             help='The number of drugs to process in each batch.'
#         )
#         parser.add_argument('--names', type=str, default=None, help='Comma-separated drug names (overrides batching)')
#         parser.add_argument('--all', action='store_true', help='Run the seeder on all drugs in the database.')

#     def handle(self, *args, **options):
#         self.stdout.write(self.style.SUCCESS('Starting hybrid fetch for detailed drug info...'))

#         api_url = 'https://api.fda.gov/drug/label.json'

#         if options['names']:
#             # (This part is unchanged)
#             name_list = [n.strip() for n in options['names'].split(',')]
#             self.stdout.write(f"FORCE PROCESSING for specific names: {name_list}")
#             name_query = Q()
#             for name in name_list:
#                 name_query |= Q(name__iexact=name)
#             drugs_to_fetch = Drug.objects.filter(name_query)
#             if not drugs_to_fetch.exists():
#                 self.stdout.write(self.style.WARNING("No drugs found with those names. Check spelling."))
#                 return
            
#             self._process_batch(drugs_to_fetch, api_url, 1, drugs_to_fetch.count(), drugs_to_fetch.count())
#             self.stdout.write(self.style.SUCCESS('\nFinished processing specified names!'))

#         elif options['all']:
#             batch_size = options['batch_size']
#             total_processed_this_run = 0
            
#             # --- THIS IS THE FIX ---
#             # We move the query *inside* the loop, so it's re-run
#             # every single time, giving us a fresh, correct count.
            
#             while True:
#                 # 1. Re-run the query to find all remaining "bad" drugs
#                 # This query finds all drugs that are NULL
#                 # OR contain any of our "fixable" bad data strings.
#                 # It will *ignore* drugs saved with PERMANENT_FALLBACK.
#                 q_filter = Q(druginfo__isnull=True)
#                 for s in BAD_DATA_STRINGS:
#                     q_filter |= Q(druginfo__side_effects__icontains=s)
#                     q_filter |= Q(druginfo__warnings__icontains=s)
#                     q_filter |= Q(druginfo__administration__icontains=s)
                
#                 base_query = Drug.objects.filter(q_filter)
#                 total_drugs_remaining = base_query.count()
#                 # --- END OF FIX ---
                
#                 self.stdout.write(self.style.SUCCESS(f"\n--- Running Batch (Total remaining to fix: {total_drugs_remaining}) ---"))
                
#                 # 2. Get the next slice of *remaining* drugs
#                 drugs_to_fetch = list(base_query.order_by('id')[:batch_size])
                
#                 if not drugs_to_fetch:
#                     self.stdout.write(self.style.SUCCESS("No more drugs to process. All done!"))
#                     break 
                
#                 # 3. Process this batch
#                 processed_count = self._process_batch(
#                     drugs_to_fetch, 
#                     api_url, 
#                     total_processed_this_run + 1, # The starting index for this batch
#                     total_drugs_remaining,
#                     len(drugs_to_fetch)
#                 )
                
#                 total_processed_this_run += processed_count
            
#             self.stdout.write(self.style.SUCCESS(f'\nFinished all batches! Total drugs processed in this run: {total_processed_this_run}'))
        
#         else:
#             self.stdout.write(self.style.ERROR("No target specified. Please use --names 'Drug,Name' or --all."))
#             return

#     def _process_batch(self, drugs_to_fetch, api_url, start_index, total_drugs_remaining, batch_size):
#         """
#         Helper function to process a list of drugs.
#         """
#         processed_count = 0
#         for i, drug in enumerate(drugs_to_fetch):
#             self.stdout.write(f'\n(Processing drug {i+1}/{batch_size} in batch. Total remaining: {total_drugs_remaining - i}) Processing: {drug.name}...')
#             try:
#                 # --- SNEAK PEEK (Current DB Data) ---
#                 try:
#                     existing_info = DrugInfo.objects.get(drug=drug)
#                     self.stdout.write(self.style.NOTICE("--- SNEAK PEEK (Current DB Data) ---"))
#                     self.stdout.write(self.style.NOTICE(f"Side Effects: '{existing_info.side_effects[:70]}...'"))
#                     self.stdout.write(self.style.NOTICE(f"Warnings:     '{existing_info.warnings[:70]}...'"))
#                     self.stdout.write(self.style.NOTICE("---------------------------------------"))
#                 except DrugInfo.DoesNotExist:
#                     self.stdout.write(self.style.NOTICE("--- SNEAK PEEK (Current DB Data) ---"))
#                     self.stdout.write(self.style.NOTICE("DrugInfo row is NULL."))
#                     self.stdout.write(self.style.NOTICE("---------------------------------------"))
#                 # --- END OF SNEAK PEEK ---

#                 se_text, warn_text, admin_text = self._fetch_openfda_fields(drug, api_url)
                
#                 combined_src = ""
#                 # --- THIS IS THE FIX for the "Acepromazine" loop ---
#                 # We check if *all* fields are empty.
#                 if not se_text and not warn_text and not admin_text:
#                     self.stdout.write(self.style.WARNING(f'   -> No OpenFDA data found for {drug.name}. Generating from scratch...'))
#                     combined_src = f"GENERATE_DATA_FOR:{drug.name}"
#                 else:
#                     self.stdout.write(self.style.SUCCESS(f'   -> OpenFDA data found for {drug.name}. Summarizing...'))
#                     combined_src = "\n\n".join([
#                         f"Drug: {drug.name}",
#                         "ADVERSE_REACTIONS:",
#                         se_text or "None listed.",
#                         "WARNINGS_AND_PRECAUTIONS:",
#                         warn_text or "None listed.",
#                         "DOSAGE_AND_ADMINISTRATION:",
#                         admin_text or "None listed."
#                     ])
                
#                 structured = summarize_structured(combined_src)
#                 debug_info = structured.get("debug", "hf_call_summarize_or_generate")
                
#                 # --- THIS IS THE FIX ---
#                 # We check if the AI *itself* failed or returned nothing
#                 # If so, we save the PERMANENT_FALLBACK text to stop the loop.
#                 if not structured.get("side_effects") and not structured.get("overview") and not structured.get("administration"):
#                     self.stdout.write(self.style.ERROR(f'   -> AI failed to generate or summarize. Saving permanent fallback.'))
#                     defaults = {
#                         'side_effects': PERMANENT_FALLBACK,
#                         'warnings': PERMANENT_FALLBACK,
#                         'administration': PERMANENT_FALLBACK
#                     }
#                 else:
#                     # AI call was successful, save the data
#                     side_effects = structured.get("side_effects") or PERMANENT_FALLBACK
#                     administration = structured.get("administration") or PERMANENT_FALLBACK
                    
#                     overview = structured.get("overview", "")
#                     interactions = structured.get("interactions", "")
                    
#                     warnings_parts = []
#                     if overview:
#                         warnings_parts.append(overview)
#                     if interactions:
#                         warnings_parts.append(f"Interactions: {interactions}")
                    
#                     warnings = "\n\n".join(warnings_parts)
#                     if not warnings:
#                         warnings = PERMANENT_FALLBACK # Use permanent fallback if warnings are empty
                    
#                     defaults = {
#                         'side_effects': side_effects,
#                         'warnings': warnings,
#                         'administration': administration
#                     }
#                 # --- END OF FIX ---

#                 # --- SNEAK PEEK: Data to be saved ---
#                 self.stdout.write(self.style.NOTICE("--- SNEAK PEEK: Data to be saved ---"))
#                 self.stdout.write(self.style.NOTICE(f"Side Effects:\n{defaults['side_effects']}"))
#                 self.stdout.write(self.style.NOTICE(f"\nWarnings:\n{defaults['warnings']}"))
#                 self.stdout.write(self.style.NOTICE(f"\nAdministration:\n{defaults['administration']}"))
#                 self.stdout.write(self.style.NOTICE("------------------------------------"))
#                 # --- END OF SNEAK PEEK ---

#                 DrugInfo.objects.update_or_create(
#                     drug=drug,
#                     defaults=defaults
#                 )
#                 self.stdout.write(self.style.SUCCESS(f'   -> Successfully saved info for {drug.name} (HF debug: {debug_info})'))
#                 processed_count += 1
#                 time.sleep(1.0) # Be nice to the API

#             except Exception as exc:
#                 logger.error(f"Error processing {drug.name}: {exc}\n{traceback.format_exc()}")
#                 self.stdout.write(self.style.ERROR(f'   -> Failed for {drug.name}; saved fallback info.'))
        
#         return processed_count


#     def _fetch_openfda_fields(self, drug: Drug, api_url: str) -> Tuple[str, str, str]:
#         """Return raw strings for adverse_reactions, warnings_and_cautions, dosage_and_administration"""
        
#         params = {'search': f'openfda.brand_name:"{drug.name}" OR openfda.generic_name:"{drug.name}"', 'limit': 1}
#         try:
#             r = requests.get(api_url, params=params, timeout=10)
#             if r.status_code != 200:
#                 logger.error(f"[_fetch_openfda_fields] OpenFDA returned {r.status_code} for {drug.name}")
#                 return "", "", ""
#             body = r.json()
#             results = body.get("results") or []
#             if not results:
#                 logger.info(f"[_fetch_openfda_fields] OpenFDA returned 0 results for {drug.name}")
#                 return "", "", ""
#             res = results[0]
#             def get_join(key):
#                 v = res.get(key)
#                 if isinstance(v, list):
#                     return "\n\n".join([str(x) for x in v if x])
#                 if isinstance(v, str):
#                     return v
#                 return ""
#             adverse = get_join("adverse_reactions") or get_join("adverse_reactions_text") or ""
#             warnings = get_join("warnings_and_cautions") or get_join("warnings_text") or ""
#             admin = get_join("dosage_and_administration") or get_join("administration_text") or ""
#             return adverse, warnings, admin
#         except requests.exceptions.RequestException as e:
#             logger.error(f"Network error fetching OpenFDA for {drug.name}: {e}")
#             return "", "", ""
# backend/drugs/management/commands/seed_druginfo.py
import time
import logging
import traceback
from typing import Tuple

import requests
from django.core.management.base import BaseCommand
from django.db.models import Q

from drugs.models import Drug, DrugInfo
from drugs.hf_summarizer import summarize_structured

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Single canonical permanent fallback used for true failures.
PERMANENT_FALLBACK = "Data not available in public databases."

# BAD_DATA_STRINGS should list only *raw-data markers* that indicate
# the original scraped/source data is problematic. Do NOT include
# messages your own script writes (we now mark auto-filled rows with auto_filled=True).
BAD_DATA_STRINGS = [
    "ADVERSE REACTIONS",
    "WARNINGS AND PRECAUTIONS",
    "No information available",
    # do NOT include "No side-effect details available" etc. — those were created by the seeder previously
]

# small helper - retry wrapper for OpenFDA calls
def _safe_get(url, params=None, timeout=10, retries=3, backoff=1.5):
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.exceptions.RequestException as e:
            logger.warning(f"OpenFDA request failed (attempt {attempt}/{retries}) for {params}: {e}")
            if attempt == retries:
                return None
            time.sleep(backoff * attempt)

class Command(BaseCommand):
    help = 'Populates the DrugInfo table using a hybrid OpenFDA + HF-API approach.'

    def add_arguments(self, parser):
        parser.add_argument('--batch_size', type=int, default=50, help='The number of drugs to process in each batch.')
        parser.add_argument('--names', type=str, default=None, help='Comma-separated drug names (overrides batching)')
        parser.add_argument('--all', action='store_true', help='Run the seeder on all drugs in the database.')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting hybrid fetch for detailed drug info...'))
        api_url = 'https://api.fda.gov/drug/label.json'

        if options['names']:
            name_list = [n.strip() for n in options['names'].split(',')]
            self.stdout.write(f"FORCE PROCESSING for specific names: {name_list}")
            name_query = Q()
            for name in name_list:
                name_query |= Q(name__iexact=name)
            drugs_to_fetch = Drug.objects.filter(name_query)
            if not drugs_to_fetch.exists():
                self.stdout.write(self.style.WARNING("No drugs found with those names. Check spelling."))
                return

            self._process_batch(drugs_to_fetch, api_url, 1, drugs_to_fetch.count(), drugs_to_fetch.count())
            self.stdout.write(self.style.SUCCESS('\nFinished processing specified names!'))

        elif options['all']:
            batch_size = options['batch_size']
            total_processed_this_run = 0

            while True:
                # Build q_filter fresh every loop. Important: exclude already auto_filled rows.
                q_filter = Q(druginfo__isnull=True) | Q(druginfo__auto_filled=False)

                # Also include any raw "bad" markers if they appear in existing druginfo fields
                for s in BAD_DATA_STRINGS:
                    q_filter |= Q(druginfo__side_effects__icontains=s)
                    q_filter |= Q(druginfo__warnings__icontains=s)
                    q_filter |= Q(druginfo__administration__icontains=s)

                # select_related('druginfo') reduces extra queries when reading existing_info
                base_query = Drug.objects.filter(q_filter).select_related('druginfo')
                total_drugs_remaining = base_query.count()

                self.stdout.write(self.style.SUCCESS(f"\n--- Running Batch (Total remaining to fix: {total_drugs_remaining}) ---"))

                drugs_to_fetch = list(base_query.order_by('id')[:batch_size])

                if not drugs_to_fetch:
                    self.stdout.write(self.style.SUCCESS("No more drugs to process. All done!"))
                    break

                processed_count = self._process_batch(
                    drugs_to_fetch,
                    api_url,
                    total_processed_this_run + 1,
                    total_drugs_remaining,
                    len(drugs_to_fetch)
                )
                total_processed_this_run += processed_count

            self.stdout.write(self.style.SUCCESS(f'\nFinished all batches! Total drugs processed in this run: {total_processed_this_run}'))

        else:
            self.stdout.write(self.style.ERROR("No target specified. Please use --names 'Drug,Name' or --all."))
            return

    def _process_batch(self, drugs_to_fetch, api_url, start_index, total_drugs_remaining, batch_size):
        processed_count = 0
        for i, drug in enumerate(drugs_to_fetch):
            self.stdout.write(f'\n(Processing drug {i+1}/{batch_size} in batch. Total remaining: {total_drugs_remaining - i}) Processing: {drug.name}...')
            try:
                # SNEAK PEEK
                try:
                    existing_info = DrugInfo.objects.get(drug=drug)
                    self.stdout.write(self.style.NOTICE("--- SNEAK PEEK (Current DB Data) ---"))
                    self.stdout.write(self.style.NOTICE(f"Side Effects: '{(existing_info.side_effects or '')[:70]}...'"))
                    self.stdout.write(self.style.NOTICE(f"Warnings:     '{(existing_info.warnings or '')[:70]}...'"))
                    self.stdout.write(self.style.NOTICE("---------------------------------------"))
                except DrugInfo.DoesNotExist:
                    self.stdout.write(self.style.NOTICE("--- SNEAK PEEK (Current DB Data) ---"))
                    self.stdout.write(self.style.NOTICE("DrugInfo row is NULL."))
                    self.stdout.write(self.style.NOTICE("---------------------------------------"))

                se_text, warn_text, admin_text = self._fetch_openfda_fields(drug, api_url)

                combined_src = ""
                if not se_text and not warn_text and not admin_text:
                    self.stdout.write(self.style.WARNING(f'   -> No OpenFDA data found for {drug.name}. Generating from scratch...'))
                    combined_src = f"GENERATE_DATA_FOR:{drug.name}"
                else:
                    self.stdout.write(self.style.SUCCESS(f'   -> OpenFDA data found for {drug.name}. Summarizing...'))
                    combined_src = "\n\n".join([
                        f"Drug: {drug.name}",
                        "ADVERSE_REACTIONS:",
                        se_text or "None listed.",
                        "WARNINGS_AND_PRECAUTIONS:",
                        warn_text or "None listed.",
                        "DOSAGE_AND_ADMINISTRATION:",
                        admin_text or "None listed."
                    ])

                structured = summarize_structured(combined_src)
                debug_info = structured.get("debug", "hf_call_summarize_or_generate")

                # If AI returned nothing useful, save the permanent fallback and mark auto_filled=True
                if not structured.get("side_effects") and not structured.get("overview") and not structured.get("administration"):
                    self.stdout.write(self.style.ERROR(f'   -> AI failed to generate or summarize. Saving permanent fallback.'))
                    defaults = {
                        'side_effects': PERMANENT_FALLBACK,
                        'warnings': PERMANENT_FALLBACK,
                        'administration': PERMANENT_FALLBACK,
                        'auto_filled': True
                    }
                else:
                    side_effects = structured.get("side_effects") or PERMANENT_FALLBACK
                    administration = structured.get("administration") or PERMANENT_FALLBACK

                    overview = structured.get("overview", "")
                    interactions = structured.get("interactions", "")

                    warnings_parts = []
                    if overview:
                        warnings_parts.append(overview)
                    if interactions:
                        warnings_parts.append(f"Interactions: {interactions}")

                    warnings = "\n\n".join(warnings_parts) if warnings_parts else PERMANENT_FALLBACK

                    defaults = {
                        'side_effects': side_effects,
                        'warnings': warnings,
                        'administration': administration,
                        'auto_filled': True
                    }

                # SNEAK PEEK: Data to be saved
                self.stdout.write(self.style.NOTICE("--- SNEAK PEEK: Data to be saved ---"))
                self.stdout.write(self.style.NOTICE(f"Side Effects:\n{defaults['side_effects']}"))
                self.stdout.write(self.style.NOTICE(f"\nWarnings:\n{defaults['warnings']}"))
                self.stdout.write(self.style.NOTICE(f"\nAdministration:\n{defaults['administration']}"))
                self.stdout.write(self.style.NOTICE("------------------------------------"))

                DrugInfo.objects.update_or_create(
                    drug=drug,
                    defaults=defaults
                )
                self.stdout.write(self.style.SUCCESS(f'   -> Successfully saved info for {drug.name} (HF debug: {debug_info})'))
                processed_count += 1
                time.sleep(1.0)

            except Exception as exc:
                logger.error(f"Error processing {drug.name}: {exc}\n{traceback.format_exc()}")
                self.stdout.write(self.style.ERROR(f'   -> Failed for {drug.name}; saved fallback info.'))

        return processed_count

    def _fetch_openfda_fields(self, drug: Drug, api_url: str) -> Tuple[str, str, str]:
        """Return raw strings for adverse_reactions, warnings_and_cautions, dosage_and_administration"""
        params = {'search': f'openfda.brand_name:"{drug.name}" OR openfda.generic_name:"{drug.name}"', 'limit': 1}
        r = _safe_get(api_url, params=params, timeout=10, retries=3)
        if not r:
            logger.error(f"[_fetch_openfda_fields] OpenFDA network error for {drug.name}")
            return "", "", ""
        try:
            body = r.json()
            results = body.get("results") or []
            if not results:
                logger.info(f"[_fetch_openfda_fields] OpenFDA returned 0 results for {drug.name}")
                return "", "", ""
            res = results[0]
            def get_join(key):
                v = res.get(key)
                if isinstance(v, list):
                    return "\n\n".join([str(x) for x in v if x])
                if isinstance(v, str):
                    return v
                return ""
            adverse = get_join("adverse_reactions") or get_join("adverse_reactions_text") or ""
            warnings = get_join("warnings_and_cautions") or get_join("warnings_text") or ""
            admin = get_join("dosage_and_administration") or get_join("administration_text") or ""
            return adverse, warnings, admin
        except ValueError:
            logger.error(f"[_fetch_openfda_fields] JSON decode error for {drug.name}")
            return "", "", ""
