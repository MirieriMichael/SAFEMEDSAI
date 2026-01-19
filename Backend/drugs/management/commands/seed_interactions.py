import os
import time
import logging
import traceback
from typing import Optional, Tuple

import requests
from django.core.management.base import BaseCommand
from django.db.models import Q

from drugs.models import Drug, DrugInfo

# local HF summarizer (HTTP-based)
from drugs.hf_summarizer import summarize_structured

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Command(BaseCommand):
    help = 'Populates the DrugInfo table using a hybrid OpenFDA + HF-API approach.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=None, help='Limit number of drugs to process')
        parser.add_argument('--offset', type=int, default=0, help='Start offset')
        parser.add_argument('--names', type=str, default=None, help='Comma-separated drug names')

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting hybrid fetch for detailed drug info...'))

        # --- THIS IS THE URL FIX ---
        api_url = 'https://api.fda.gov/drug/label.json' # Added 'https://'
        # --- END OF URL FIX ---

        # --- THIS IS THE FINAL AGGRESSIVE FILTER ---
        base_query = Drug.objects.filter(
            Q(druginfo__isnull=True) |
            Q(druginfo__side_effects__icontains='No information available') |
            Q(druginfo__warnings__icontains='No information available') |
            Q(druginfo__side_effects__icontains='No AI summary available') |
            Q(druginfo__warnings__icontains='No AI summary available') |
            Q(druginfo__side_effects__icontains='Error:') |
            Q(druginfo__warnings__icontains='Error:') |
            Q(druginfo__side_effects='') |
            Q(druginfo__warnings='') |
            Q(druginfo__side_effects='N/A') |
            Q(druginfo__warnings='N/A') |
            Q(druginfo__side_effects__startswith='6 ADVERSE REACTIONS') |
            Q(druginfo__warnings__startswith='5 WARNINGS AND PRECAUTIONS') |
            # --- THE FIX FROM YOUR SCREENSHOT ---
            Q(druginfo__side_effects__icontains='No detailed side effect information available') |
            Q(druginfo__warnings__icontains='No detailed warning information available')
            # --- END OF FIX ---
        )

        if options['names']:
            name_list = [n.strip() for n in options['names'].split(',')]
            self.stdout.write(f"Filtering for specific names: {name_list}")
            
            # Use the simple, case-sensitive filter
            base_query = base_query.filter(name__in=name_list)

        offset = options['offset']
        limit = options['limit']

        total_drugs = base_query.distinct().count() 
        drugs_to_fetch = base_query.distinct().order_by('name')[offset:] 
        if limit:
            drugs_to_fetch = drugs_to_fetch[:limit]

        self.stdout.write(f'Found {total_drugs} total drugs to process. This batch will run {len(drugs_to_fetch)} drugs.')

        for i, drug in enumerate(drugs_to_fetch):
            self.stdout.write(f'\n({i+1+offset}/{total_drugs}) Processing: {drug.name}...')
            try:
                se_text, warn_text, admin_text = self._fetch_openfda_fields(drug, api_url)
                
                if not se_text and not warn_text and not admin_text:
                    self.stdout.write(self.style.WARNING(f'  -> No OpenFDA data found for {drug.name}. Saving fallback text.'))
                    side_effects = "No detailed side effect information available. Consult product leaflet or a clinician."
                    warnings = "No detailed warning information available. Consult product leaflet or a clinician."
                    administration = "No detailed administration information available. Consult product leaflet or a clinician."
                    debug_info = "no_openfda_data"
                
                else:
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
                    debug_info = structured.get("debug", "hf_call_unknown")

                    side_effects = structured.get("side_effects") or "No side-effect details available. Consult product leaflet or a clinician."
                    warnings = structured.get("warnings") or "No warning details available. Consult product leaflet or a clinician."
                    administration = structured.get("administration") or "No administration details available. Consult product leaflet or a clinician."
                    
                    overview = structured.get("overview", "")
                    if overview:
                        warnings = (overview + "\n\n" + warnings).strip()
                
                # --- "SNEAK PEEK" ---
                self.stdout.write(self.style.NOTICE("--- SNEAK PEEK: Data to be saved ---"))
                self.stdout.write(self.style.NOTICE(f"Side Effects:\n{side_effects}"))
                self.stdout.write(self.style.NOTICE(f"\nWarnings:\n{warnings}"))
                self.stdout.write(self.style.NOTICE(f"\nAdministration:\n{administration}"))
                self.stdout.write(self.style.NOTICE("------------------------------------"))
                # --- END OF SNEAK PEEK ---

                DrugInfo.objects.update_or_create(
                    drug=drug,
                    defaults={
                        'side_effects': side_effects,
                        'warnings': warnings,
                        'administration': administration
                    }
                )
                self.stdout.write(self.style.SUCCESS(f'  -> Successfully saved info for {drug.name} (HF debug: {debug_info})'))

                time.sleep(1.0) # Be nice to the API

            except Exception as exc:
                logger.error(f"Error processing {drug.name}: {exc}\n{traceback.format_exc()}")
                DrugInfo.objects.update_or_create(
                    drug=drug,
                    defaults={
                        'side_effects': "Failed to fetch side-effect info. See product leaflet.",
                        'warnings': "Failed to fetch warnings. See product leaflet.",
                        'administration': "Failed to fetch administration instructions. See product leaflet."
                    }
                )
                self.stdout.write(self.style.ERROR(f'  -> Failed for {drug.name}; saved fallback info.'))

        self.stdout.write(self.style.SUCCESS('\nFinished batch!'))

    def _fetch_openfda_fields(self, drug: Drug, api_url: str) -> Tuple[str, str, str]:
        """Return raw strings for adverse_reactions, warnings_and_cautions, dosage_and_administration"""
        params = {'search': f'openfda.brand_name:"{drug.name}" OR openfda.generic_name:"{drug.name}"', 'limit': 1}
        try:
            r = requests.get(api_url, params=params, timeout=10)
            if r.status_code != 200:
                logger.info(f"[_fetch_openfda_fields] OpenFDA returned {r.status_code} for {drug.name}")
                return "", "", ""
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
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching OpenFDA for {drug.name}: {e}")
            return "", "", ""