# backend/drugs/management/commands/seed_interactions.py
import requests
import time
from django.core.management.base import BaseCommand
from django.db import transaction
from drugs.models import Drug, Interaction

class Command(BaseCommand):
    help = 'Populates the Interaction table by fetching and parsing data from the OpenFDA API.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to seed drug interactions from OpenFDA...'))
        
        api_url = 'https://api.fda.gov/drug/label.json'
        
        all_drugs = list(Drug.objects.all())
        all_drug_names = set(drug.name.lower() for drug in all_drugs)
        
        interactions_to_create = []
        total_created_count = 0
        batch_size = 100 # --- We will save to the DB every 100 drugs ---

        total_drugs = len(all_drugs)
        self.stdout.write(f'Found {total_drugs} drugs to check for interactions.')

        for i, drug_a in enumerate(all_drugs):
            self.stdout.write(f'({i+1}/{total_drugs}) Processing: {drug_a.name}...')
            
            params = {
                'search': f'openfda.brand_name:"{drug_a.name}" OR openfda.generic_name:"{drug_a.name}"',
                'limit': 1
            }
            
            try:
                response = requests.get(api_url, params=params)
                
                if response.status_code == 200 and response.json().get('results'):
                    result = response.json()['results'][0]
                    interaction_text_list = result.get('drug_interactions')
                    if interaction_text_list:
                        interaction_text = interaction_text_list[0].lower()
                        
                        for drug_b_name in all_drug_names:
                            if drug_b_name != drug_a.name.lower() and f' {drug_b_name} ' in interaction_text:
                                drug_b = next((d for d in all_drugs if d.name.lower() == drug_b_name), None)
                                if drug_b:
                                    sorted_drugs = sorted([drug_a, drug_b], key=lambda d: d.id)
                                    interactions_to_create.append(
                                        Interaction(
                                            drug_a=sorted_drugs[0],
                                            drug_b=sorted_drugs[1],
                                            description=interaction_text_list[0],
                                            severity='UNKNOWN'
                                        )
                                    )

            except requests.exceptions.RequestException:
                self.stdout.write(self.style.WARNING(f'  -> Network error for {drug_a.name}'))

            time.sleep(0.1)

            # --- NEW: Save in batches ---
            # If we have processed a full batch OR if this is the very last drug
            if (i + 1) % batch_size == 0 or (i + 1) == total_drugs:
                if interactions_to_create:
                    try:
                        with transaction.atomic():
                            Interaction.objects.bulk_create(interactions_to_create, ignore_conflicts=True)
                            self.stdout.write(self.style.SUCCESS(f'  -> Saved a batch of {len(interactions_to_create)} interactions.'))
                            total_created_count += len(interactions_to_create)
                            interactions_to_create = [] # Clear the list for the next batch
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  -> An error occurred during batch save: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Interaction seeding complete! Total interactions created: {total_created_count}'))