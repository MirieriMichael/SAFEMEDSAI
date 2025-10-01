# backend/drugs/management/commands/seed_openfda.py
import requests
import time
from django.core.management.base import BaseCommand
from drugs.models import Drug, DrugInfo

class Command(BaseCommand):
    help = 'Populates the DrugInfo table by fetching data from the OpenFDA API.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to fetch detailed drug info from OpenFDA...'))
        
        # Base URL for the OpenFDA drug label API
        api_url = 'https://api.fda.gov/drug/label.json'
        
        # Get all drugs that do not have a DrugInfo entry yet.
        drugs_to_fetch = Drug.objects.filter(druginfo__isnull=True)
        total_drugs = drugs_to_fetch.count()
        self.stdout.write(f'Found {total_drugs} drugs without detailed info.')

        # This entire 'for' loop MUST be indented to be inside the 'handle' method
        for i, drug in enumerate(drugs_to_fetch):
            self.stdout.write(f'({i+1}/{total_drugs}) Fetching info for: {drug.name}...')
            
            # 1. Get the core drug name (usually the first word)
            core_drug_name = drug.name.split(' ')[0]

            # 2. Create a search term without strict quotes
            search_term = f'openfda.generic_name:{core_drug_name} OR openfda.brand_name:{core_drug_name}'
    
            # 3. Construct the final parameters for the API call
            params = {
                'search': search_term,
                'limit': 1
            }
            
            try:
                # Make the API request
                response = requests.get(api_url, params=params)
                
                # Check if the request was successful and if there are results
                if response.status_code == 200 and response.json().get('results'):
                    result = response.json()['results'][0]
                    
                    # Safely get data from the JSON response.
                    side_effects = result.get('adverse_reactions', ['No information available.'])[0]
                    warnings = result.get('warnings_and_cautions', ['No information available.'])[0]
                    administration = result.get('dosage_and_administration', ['No information available.'])[0]
                    
                    # Use update_or_create to add the DrugInfo for the drug.
                    DrugInfo.objects.update_or_create(
                        drug=drug,
                        defaults={
                            'side_effects': side_effects,
                            'warnings': warnings,
                            'administration': administration
                        }
                    )
                else:
                    # This handles the case where a drug is not found in OpenFDA.
                    self.stdout.write(self.style.WARNING(f'  -> No data found for {drug.name}'))

            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f'  -> A network error occurred for {drug.name}: {e}'))
            
            # Be polite to the API: wait a fraction of a second between requests
            time.sleep(0.1)

        # This final message must also be indented inside the 'handle' method
        self.stdout.write(self.style.SUCCESS('Finished fetching detailed drug info!'))