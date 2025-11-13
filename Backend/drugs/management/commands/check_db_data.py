# backend/drugs/management/commands/check_db_data.py
from django.core.management.base import BaseCommand
from django.db.models import Q
from drugs.models import DrugInfo

class Command(BaseCommand):
    help = 'Checks the database for drugs with missing or fallback data.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Checking database for drugs with fallback data..."))

        # Define the fallback strings we're looking for
        fallback_strings = [
            "No side-effect details available",
            "No warning details available",
            "No administration details available"
        ]

        # Build a query to find any record containing any of these strings
        query = Q()
        for s in fallback_strings:
            query |= Q(side_effects__icontains=s)
            query |= Q(warnings__icontains=s)
            query |= Q(administration__icontains=s)

        # Find all DrugInfo objects that match the query
        bad_data_drugs = DrugInfo.objects.filter(query)
        
        count = bad_data_drugs.count()

        if count > 0:
            self.stdout.write(self.style.ERROR(f"\nFound {count} drugs with missing/fallback data:"))
            for info in bad_data_drugs:
                self.stdout.write(f"- {info.drug.name}")
            
            self.stdout.write(self.style.WARNING("\nThese drugs can be manually fixed in the Django Admin."))
        else:
            self.stdout.write(self.style.SUCCESS("\nNo drugs with fallback data found! All drugs have summaries."))