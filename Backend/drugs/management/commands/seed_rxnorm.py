# backend/drugs/management/commands/seed_rxnorm.py
import csv
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from drugs.models import Drug

class Command(BaseCommand):
    help = 'Seeds the database with drug data from the RxNorm RRF files.'

    # The 'handle' method MUST be indented to be part of the Command class
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting RxNorm database seeding...'))

        # This is the corrected, simpler path logic
        conso_file_path = os.path.join(settings.BASE_DIR, 'data', 'rrf', 'RXNCONSO.RRF')

        if not os.path.exists(conso_file_path):
            self.stdout.write(self.style.ERROR(f'RXNCONSO.RRF not found at: {conso_file_path}'))
            return

        drugs_to_create = []
        seen_drug_names = set(Drug.objects.values_list('name', flat=True))

        self.stdout.write(f'Reading from {conso_file_path}...')
        
        # Open and read the RXNCONSO.RRF file
        with open(conso_file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter='|')
            for row in reader:
                # Column 1 is language (we only want English)
                # Column 12 is Term Type (TTY). 'IN' = Ingredient, 'BN' = Brand Name.
                # These are the most useful terms for our application.
                if row and len(row) > 14 and row[1] == 'ENG' and row[12] in ['IN', 'BN']:
                    drug_name = row[14].strip().capitalize()
                    # Add the drug if it's new
                    if drug_name and drug_name not in seen_drug_names:
                        drugs_to_create.append(Drug(name=drug_name))
                        seen_drug_names.add(drug_name)

        # Use a transaction and bulk_create for high performance
        try:
            with transaction.atomic():
                if drugs_to_create:
                    Drug.objects.bulk_create(drugs_to_create, batch_size=1000)
                    self.stdout.write(self.style.SUCCESS(f'Successfully created {len(drugs_to_create)} new drug entries.'))
                else:
                    self.stdout.write(self.style.SUCCESS('No new drugs to add. Database is up to date.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {e}'))

        self.stdout.write(self.style.SUCCESS('RxNorm seeding complete!'))