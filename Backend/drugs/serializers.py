# backend/drugs/serializers.py
from rest_framework import serializers
# --- ADD THIS: Import DrugInfo and ScanHistory ---
from .models import Drug, Interaction, DrugInfo, ScanHistory,Profile, Notification
# --- END ADD ---

# NEW serializer for our detailed info model
class DrugInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DrugInfo
        fields = ['administration', 'side_effects', 'warnings']

class DrugSerializer(serializers.ModelSerializer):
    """UPDATED to include the nested DrugInfo."""
    druginfo = DrugInfoSerializer(read_only=True)

    class Meta:
        model = Drug
        # Using the fields from your model + the new druginfo
        fields = ['id', 'name', 'rxcui', 'is_brand', 'druginfo']

class InteractionSerializer(serializers.ModelSerializer):
    """This serializer remains the same, but will now show more detail
       because it uses the updated DrugSerializer."""
    drug_a = DrugSerializer(read_only=True)
    drug_b = DrugSerializer(read_only=True)

    class Meta:
        model = Interaction
        fields = ['drug_a', 'drug_b', 'description', 'severity']

# ... (DrugInfoSerializer, DrugSerializer, InteractionSerializer remain unchanged) ...

class ScanHistorySerializer(serializers.ModelSerializer):
    """
    Serializes the ScanHistory model.
    """
    class Meta:
        model = ScanHistory
        # --- THIS IS THE FIX ---
        # I added 'scan_results' to this list. 
        # Before, it was missing, so the frontend got nothing.
        fields = ['id', 'created_at', 'drug_names', 'scan_results'] 
        # --- END FIX ---
# backend/drugs/serializers.py
# ... (existing serializers)

# backend/drugs/serializers.py

# ... imports ...

class ProfileSerializer(serializers.ModelSerializer):
    # We add 'avatar_url' to help the frontend display it easily
    avatar_url = serializers.SerializerMethodField()
    # Explicitly allow avatar to be optional in partial updates
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Profile
        fields = ['allergies', 'conditions', 'phone_number', 'birth_date', 'avatar', 'avatar_url']

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'is_read', 'created_at', 'type']