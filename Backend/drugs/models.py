# backend/drugs/models.py
from django.db import models

class Drug(models.Model):
    name = models.CharField(max_length=200, unique=True, db_index=True)

    def __str__(self):
        return self.name

# ADD THIS NEW MODEL
class DrugInfo(models.Model):
    """Stores detailed information about a specific drug."""
    # This creates a one-to-one link to the main Drug table.
    drug = models.OneToOneField(Drug, on_delete=models.CASCADE, primary_key=True)
    administration = models.TextField(blank=True, null=True) # How to take the drug
    side_effects = models.TextField(blank=True, null=True)
    warnings = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Info for {self.drug.name}"


class Interaction(models.Model):
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

    def __str__(self):
        return f"{self.drug_a.name} <-> {self.drug_b.name}"