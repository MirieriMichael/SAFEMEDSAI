# backend/drugs/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Drug, Interaction
# UPDATE serializers import
from .serializers import InteractionSerializer, DrugSerializer
from itertools import combinations
from django.db.models import Q

class InteractionCheckView(APIView):
    def post(self, request, *args, **kwargs):
        drug_names = request.data.get('drugs', [])
        if not drug_names or len(drug_names) < 2:
            return Response(
                {"error": "Please provide at least two drug names."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find all Drug objects from the input list.
        # `prefetch_related` is a performance optimization to get all DrugInfo objects in one extra query.
        drugs_in_query = Drug.objects.filter(name__in=drug_names).prefetch_related('druginfo')

        # --- Interaction Logic (Same as before) ---
        drug_pairs = list(combinations(drugs_in_query, 2))
        found_interactions = []
        for pair in drug_pairs:
            interaction = Interaction.objects.filter(
                (Q(drug_a=pair[0]) & Q(drug_b=pair[1])) | 
                (Q(drug_a=pair[1]) & Q(drug_b=pair[0]))
            ).first()
            if interaction:
                found_interactions.append(interaction)

        # --- NEW: Serialize all queried drugs for their detailed info ---
        drug_details_serializer = DrugSerializer(drugs_in_query, many=True)
        interaction_serializer = InteractionSerializer(found_interactions, many=True)

        # --- NEW: Return a structured response with both interactions and drug details ---
        response_data = {
            'interactions': interaction_serializer.data,
            'drug_details': drug_details_serializer.data
        }

        return Response(response_data, status=status.HTTP_200_OK)