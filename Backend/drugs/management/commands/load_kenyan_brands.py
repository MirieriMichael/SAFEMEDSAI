# Backend/drugs/management/commands/load_kenyan_brands.py

import os
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from drugs.models import LocalBrand
import time # To show how fast it is

class Command(BaseCommand):
    help = 'Loads Kenyan drug brands from an Excel file using bulk_create'

    def handle(self, *args, **options):
        
        file_path = os.path.join(settings.BASE_DIR, 'data', 'Kenyameds', 'kenya_drugs.xlsx')

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found at: {file_path}'))
            return

        self.stdout.write(f"Opening Excel file: {file_path}")
        
        try:
            start_time = time.time()
            
            df = pd.read_excel(file_path, sheet_name=0) 
            
            if 'Brand Name' not in df.columns or 'Generic Name' not in df.columns:
                self.stdout.write(self.style.ERROR('Error: Columns "Brand Name" and "Generic Name" not found.'))
                return

            brands_to_create = []
            seen_brand_names = set()
            
            self.stdout.write(f"Reading {len(df)} rows from Excel...")

            # 1. LOOP IN MEMORY (Fast)
            for index, row in df.iterrows():
                brand_name = row['Brand Name']
                ingredients_str = row['Generic Name']

                if pd.isna(brand_name) or pd.isna(ingredients_str):
                    continue
                
                brand_name_clean = brand_name.strip()
                
                # Skip duplicates within the Excel file itself
                if not brand_name_clean or brand_name_clean in seen_brand_names:
                    continue

                ingredients_list = [
                    name.strip() for name in str(ingredients_str).split(',') if name.strip()
                ]

                if not ingredients_list:
                    continue
                
                # Add to our list in memory
                brands_to_create.append(
                    LocalBrand(
                        brand_name=brand_name_clean,
                        generic_names=ingredients_list,
                        source_dataset='Kenya Kaggle'
                    )
                )
                seen_brand_names.add(brand_name_clean)

            self.stdout.write(f"Prepared {len(brands_to_create)} unique brands for import.")
            
            # 2. SEND TO DB IN ONE GO (Super Fast)
            self.stdout.write("Sending bulk create command to database...")
            LocalBrand.objects.bulk_create(
                brands_to_create,
                batch_size=1000,  # Send in chunks of 1000
                update_conflicts=True, # This means "if brand_name exists, update it"
                unique_fields=['brand_name'],
                update_fields=['generic_names', 'source_dataset']
            )

            end_time = time.time()
            self.stdout.write(self.style.SUCCESS(f'Successfully loaded {len(brands_to_create)} brands in {end_time - start_time:.2f} seconds.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {e}'))