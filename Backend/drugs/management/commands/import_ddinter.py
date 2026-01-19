# backend/drugs/management/commands/import_ddinter.py
import csv
import os
import glob
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import IntegrityError
from drugs.models import Interaction, Drug  # Import both models
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(asctime)s:%(message)s")

# Map CSV severity levels to our model's choices
SEVERITY_MAP = {
    'major': 'MAJOR',
    'moderate': 'MODERATE',
    'minor': 'MINOR',
    'unknown': 'UNKNOWN',
}

class Command(BaseCommand):
    help = 'Imports drug interaction data from the DDInter CSV files'

    def handle(self, *args, **options):
        data_dir = os.path.join(settings.BASE_DIR, 'data', 'ddinter')
        
        if not os.path.isdir(data_dir):
            raise CommandError(f'Directory not found: {data_dir}. Please create it and add your CSVs.')

        csv_files = glob.glob(os.path.join(data_dir, 'ddinter_downloads_code_*.csv'))
        
        if not csv_files:
            raise CommandError(f'No "ddinter_downloads_code_*.csv" files found in {data_dir}.')

        self.stdout.write(f"Found {len(csv_files)} DDInter files. Starting import...")
        
        # Cache for found drugs to speed up the import
        self.stdout.write("Caching all drug names from database for faster lookups...")
        drug_cache = {drug.name.lower(): drug for drug in Drug.objects.all()}
        self.stdout.write(f"Cached {len(drug_cache)} drug names.")

        total_imported = 0
        total_skipped = 0
        
        for file_path in csv_files:
            self.stdout.write(f"\nProcessing file: {os.path.basename(file_path)}...")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                interactions_to_create = []

                for row_num, row in enumerate(reader, 1):
                    try:
                        drug_a_name = row['Drug_A'].strip()
                        drug_b_name = row['Drug_B'].strip()
                        
                        # Find Drug A in our cache
                        drug_a = drug_cache.get(drug_a_name.lower())
                        
                        # Find Drug B in our cache
                        drug_b = drug_cache.get(drug_b_name.lower())

                        if not drug_a or not drug_b:
                            # This happens if 'Drug_A' or 'Drug_B' from the CSV
                            # is not in your 'Drug' table. This is GOOD, it keeps
                            # your data clean.
                            total_skipped += 1
                            # logging.warning(f"Skipping row {row_num}: Cannot find Drug '{drug_a_name}' or '{drug_b_name}' in database.")
                            continue

                        # Get severity and map it
                        csv_severity = row.get('Level', 'unknown').lower()
                        model_severity = SEVERITY_MAP.get(csv_severity, 'UNKNOWN')
                        
                        csv_description = row.get('Interaction Description', row.get('Interaction', 'No description available.'))
                        
                        # Sort by ID to ensure (drug_a, drug_b) is always consistent
                        if drug_a.id < drug_b.id:
                            i_drug_a, i_drug_b = drug_a, drug_b
                        else:
                            i_drug_a, i_drug_b = drug_b, drug_a
                        
                        interactions_to_create.append(
                            Interaction(
                                drug_a=i_drug_a,
                                drug_b=i_drug_b,
                                severity=model_severity,
                                description=csv_description
                            )
                        )
                    
                    except Exception as e:
                        self.stderr.write(f"Error processing row {row_num}: {row} | Error: {e}")
                        total_skipped += 1
                
                # Bulk create this file's interactions
                try:
                    Interaction.objects.bulk_create(interactions_to_create, ignore_conflicts=True)
                    total_imported += len(interactions_to_create)
                    self.stdout.write(f"Processed file. Imported {total_imported} total so far... Skipped {total_skipped}...")
                except IntegrityError as e:
                    self.stderr.write(f"Bulk create error (likely duplicates): {e}")
                except Exception as e:
                    self.stderr.write(f"Bulk create error: {e}")

        self.stdout.write(self.style.SUCCESS(f'\nImport complete! Successfully imported {total_imported} interactions. Skipped {total_skipped} rows (drugs not found).'))