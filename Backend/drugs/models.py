# backend/drugs/models.py
from django.db import models
from django.db.models import Q
from itertools import combinations
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(asctime)s:%(message)s")

class Drug(models.Model):
    # Increased max_length and added fields for RxNorm data and OCR logic
    name = models.CharField(max_length=500, unique=True, db_index=True)
    rxcui = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    is_brand = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class DrugInfo(models.Model):
    """Stores detailed information about a specific drug."""
    # This is your model, it's perfect.
    drug = models.OneToOneField(Drug, on_delete=models.CASCADE, primary_key=True)
    administration = models.TextField(blank=True, null=True) # How to take the drug
    side_effects = models.TextField(blank=True, null=True)
    warnings = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Info for {self.drug.name}"

class Interaction(models.Model):
    """
    This is your model structure, which is excellent.
    It uses ForeignKeys to link directly to the Drug table.
    """
    SEVERITY_CHOICES = [
        ('MINOR', 'Minor'),
        ('MODERATE', 'Moderate'),
        ('MAJOR', 'Major'),
        ('UNKNOWN', 'Unknown'),
    ]

    drug_a = models.ForeignKey(Drug, related_name='interactions_a', on_delete=models.CASCADE)
    drug_b = models.ForeignKey(Drug, related_name='interactions_b', on_delete=models.CASCADE)
    description = models.TextField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='UNKNOWN')

    class Meta:
        unique_together = ('drug_a', 'drug_b')
        # Add an index for faster lookups
        indexes = [
            models.Index(fields=['drug_a', 'drug_b']),
        ]

    def __str__(self):
        return f"{self.drug_a.name} <-> {self.drug_b.name}"

    @staticmethod
    def get_interactions(drug_names: list) -> list:
        """
        Queries the database for interactions between a list of drug names.
        This static method is now adapted to your ForeignKey model.
        """
        if len(drug_names) < 2:
            return []

        interactions_found = []
        
        # Create all possible unique pairs, e.g., [(A, B), (A, C), (B, C)]
        possible_pairs = list(combinations(drug_names, 2))

        for name1, name2 in possible_pairs:
            # This query is powerful. It joins the Interaction table with the
            # Drug table *twice* to check the names, all in one DB call.
            # It checks for (A, B) and (B, A) at the same time.
            query = (
                Q(drug_a__name__iexact=name1, drug_b__name__iexact=name2) |
                Q(drug_a__name__iexact=name2, drug_b__name__iexact=name1)
            )
            
            results = Interaction.objects.filter(query).select_related('drug_a', 'drug_b')

            for interaction in results:
                interactions_found.append({
                    'drug_1': interaction.drug_a.name,
                    'drug_2': interaction.drug_b.name,
                    'description': interaction.description,
                    'severity': interaction.get_severity_display(), # Uses the display value (e.g., "Minor")
                })
        
        if interactions_found:
            # We must de-duplicate the results, as the query might find both (A,B) and (B,A)
            # if the logic runs twice.
            seen_pairs = set()
            final_list = []
            for interaction in interactions_found:
                pair_key = tuple(sorted([interaction['drug_1'], interaction['drug_2']]))
                if pair_key not in seen_pairs:
                    final_list.append(interaction)
                    seen_pairs.add(pair_key)
            
            logging.info(f"Found {len(final_list)} unique interactions locally for {drug_names}")
            return final_list
            
        return []