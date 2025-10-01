# backend/drugs/serializers.py
from rest_framework import serializers
from .models import Drug, Interaction, DrugInfo # Import DrugInfo

# NEW serializer for our detailed info model
class DrugInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DrugInfo
        fields = ['administration', 'side_effects', 'warnings']

class DrugSerializer(serializers.ModelSerializer):
    """UPDATED to include the nested DrugInfo."""
    # This line tells the serializer to look for the related DrugInfo object
    # and use the DrugInfoSerializer to format it.
    druginfo = DrugInfoSerializer(read_only=True)

    class Meta:
        model = Drug
        fields = ['name', 'druginfo'] # Add 'druginfo' to the fields

class InteractionSerializer(serializers.ModelSerializer):
    """This serializer remains the same, but will now show more detail
       because it uses the updated DrugSerializer."""
    drug_a = DrugSerializer(read_only=True)
    drug_b = DrugSerializer(read_only=True)

    class Meta:
        model = Interaction
        fields = ['drug_a', 'drug_b', 'description', 'severity']