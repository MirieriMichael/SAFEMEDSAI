from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.http import HttpResponse
import csv
from .models import Drug, DrugInfo, Interaction, LocalBrand, Profile, ScanHistory, Notification


# ============================================
# DRUG ADMIN CONFIGURATION
# ============================================
@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    """
    Custom admin interface for Drug model.
    """
    
    # --- LIST VIEW CONFIGURATION ---
    list_display = ('name', 'get_active_ingredients', 'has_warnings', 'is_brand', 'rxcui')
    list_filter = ('is_brand',)
    search_fields = ('name', 'rxcui', 'druginfo__warnings')  # Search by name, rxcui, and warnings
    readonly_fields = ('get_active_ingredients', 'has_warnings_display')
    actions = ['export_as_csv', 'mark_as_brand']
    
    # --- DETAIL VIEW CONFIGURATION ---
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'rxcui', 'is_brand', 'get_active_ingredients')
        }),
        ('Medical Warnings', {
            'fields': ('has_warnings_display',),
            'classes': ('collapse',),
            'description': 'Warning information is stored in the related DrugInfo model.'
        }),
    )
    
    # --- CUSTOM METHODS ---
    def get_active_ingredients(self, obj):
        """
        Display active ingredients from related DrugInfo or LocalBrand.
        """
        # Try to get from LocalBrand first
        try:
            local_brand = LocalBrand.objects.get(brand_name__iexact=obj.name)
            if local_brand.generic_names:
                return ', '.join(local_brand.generic_names) if isinstance(local_brand.generic_names, list) else str(local_brand.generic_names)
        except LocalBrand.DoesNotExist:
            pass
        
        # Fallback: return drug name if no ingredients found
        return obj.name or 'N/A'
    get_active_ingredients.short_description = 'Active Ingredients'
    
    def has_warnings(self, obj):
        """
        Check if drug has warnings in DrugInfo.
        Returns HTML badge (NOT boolean - removed boolean=True to fix KeyError).
        """
        try:
            druginfo = obj.druginfo
            has_warnings = bool(druginfo.warnings and druginfo.warnings.strip())
        except DrugInfo.DoesNotExist:
            has_warnings = False
        
        if has_warnings:
            return format_html('<span style="color: red; font-weight: bold;">⚠️ Yes</span>')
        return format_html('<span style="color: green; font-weight: bold;">✓ No</span>')
    # REMOVED: has_warnings.boolean = True  # This was causing KeyError with format_html
    has_warnings.short_description = 'Has Warnings?'
    
    def has_warnings_display(self, obj):
        """
        Display warnings in the detail view.
        """
        try:
            druginfo = obj.druginfo
            if druginfo.warnings and druginfo.warnings.strip():
                return format_html('<div style="background: #fff3cd; padding: 10px; border-radius: 4px;">{}</div>', 
                                 druginfo.warnings)
            return 'No warnings available.'
        except DrugInfo.DoesNotExist:
            return 'No drug information available.'
    has_warnings_display.short_description = 'Warnings'
    # Note: allow_tags is deprecated in Django 1.9+, format_html handles HTML safely
    
    def get_queryset(self, request):
        """
        Optimize queries by selecting related DrugInfo.
        """
        qs = super().get_queryset(request)
        return qs.select_related('druginfo').prefetch_related('druginfo')
    
    # --- ADMIN ACTIONS ---
    def export_as_csv(self, request, queryset):
        """
        Export selected drugs to CSV.
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="drugs_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Name', 'RXCUI', 'Is Brand', 'Active Ingredients', 'Has Warnings', 'Administration', 'Side Effects', 'Warnings'])
        
        for drug in queryset:
            # Get active ingredients
            ingredients = 'N/A'
            try:
                local_brand = LocalBrand.objects.get(brand_name__iexact=drug.name)
                if local_brand.generic_names:
                    ingredients = ', '.join(local_brand.generic_names) if isinstance(local_brand.generic_names, list) else str(local_brand.generic_names)
            except LocalBrand.DoesNotExist:
                ingredients = drug.name
            
            # Get drug info
            has_warnings = 'No'
            administration = ''
            side_effects = ''
            warnings = ''
            try:
                druginfo = drug.druginfo
                has_warnings = 'Yes' if (druginfo.warnings and druginfo.warnings.strip()) else 'No'
                administration = druginfo.administration or ''
                side_effects = druginfo.side_effects or ''
                warnings = druginfo.warnings or ''
            except DrugInfo.DoesNotExist:
                pass
            
            writer.writerow([
                drug.name,
                drug.rxcui or '',
                'Yes' if drug.is_brand else 'No',
                ingredients,
                has_warnings,
                administration[:200],  # Truncate long text
                side_effects[:200],
                warnings[:200],
            ])
        
        return response
    export_as_csv.short_description = "Export selected drugs to CSV"
    
    def mark_as_brand(self, request, queryset):
        """
        Bulk action: Mark selected drugs as brand names.
        """
        updated = queryset.update(is_brand=True)
        self.message_user(request, f'{updated} drug(s) marked as brand names.')
    mark_as_brand.short_description = "Mark selected drugs as brand names"


# ============================================
# DRUG INFO ADMIN (INLINE)
# ============================================
class DrugInfoInline(admin.StackedInline):
    """
    Inline admin for DrugInfo, shown within Drug admin.
    """
    model = DrugInfo
    extra = 0
    fields = ('administration', 'side_effects', 'warnings', 'auto_filled', 'updated_at')
    readonly_fields = ('updated_at',)


# Add inline to DrugAdmin
DrugAdmin.inlines = [DrugInfoInline]


# ============================================
# PROFILE ADMIN CONFIGURATION
# ============================================
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Custom admin interface for Profile (UserProfile) model.
    """
    
    list_display = ('get_username', 'get_email', 'scan_count', 'email_verified', 'is_2fa_enabled')
    list_filter = ('email_verified', 'is_2fa_enabled', 'user__date_joined')
    search_fields = ('user__username', 'user__email', 'phone_number')
    readonly_fields = ('user', 'scan_count', 'get_username', 'get_email')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'get_username', 'get_email', 'scan_count')
        }),
        ('Personal Information', {
            'fields': ('phone_number', 'birth_date', 'avatar')
        }),
        ('Medical Information', {
            'fields': ('allergies', 'conditions'),
            'classes': ('collapse',)
        }),
        ('Security & Verification', {
            'fields': ('email_verified', 'verification_token', 'is_2fa_enabled', 'otp_code', 'otp_created_at')
        }),
    )
    
    def get_username(self, obj):
        """Display username from related User."""
        return obj.user.username if obj.user else 'N/A'
    get_username.short_description = 'Username'
    
    def get_email(self, obj):
        """Display email from related User."""
        return obj.user.email if obj.user else 'N/A'
    get_email.short_description = 'Email'
    
    def scan_count(self, obj):
        """Count of saved scans for this user."""
        if obj.user:
            return ScanHistory.objects.filter(user=obj.user).count()
        return 0
    scan_count.short_description = 'Saved Scans'
    
    def get_queryset(self, request):
        """Optimize queries by selecting related User."""
        qs = super().get_queryset(request)
        return qs.select_related('user')


# ============================================
# INTERACTION ADMIN
# ============================================
@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    """
    Admin interface for drug interactions.
    """
    list_display = ('drug_a', 'drug_b', 'severity', 'get_description_preview')
    list_filter = ('severity',)
    search_fields = ('drug_a__name', 'drug_b__name', 'description')
    
    def get_description_preview(self, obj):
        """Show first 100 characters of description."""
        if obj.description:
            return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
        return 'No description'
    get_description_preview.short_description = 'Description Preview'


# ============================================
# LOCAL BRAND ADMIN
# ============================================
@admin.register(LocalBrand)
class LocalBrandAdmin(admin.ModelAdmin):
    """
    Admin interface for local brand mappings.
    """
    list_display = ('brand_name', 'get_generic_names_display', 'source_dataset')
    search_fields = ('brand_name',)
    list_filter = ('source_dataset',)
    
    def get_generic_names_display(self, obj):
        """Display generic names as comma-separated list."""
        if isinstance(obj.generic_names, list):
            return ', '.join(obj.generic_names)
        return str(obj.generic_names)
    get_generic_names_display.short_description = 'Generic Names'


# ============================================
# SCAN HISTORY ADMIN
# ============================================
@admin.register(ScanHistory)
class ScanHistoryAdmin(admin.ModelAdmin):
    """
    Admin interface for user scan history.
    """
    list_display = ('user', 'created_at', 'get_drug_names_display')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    def get_drug_names_display(self, obj):
        """Display drug names from JSON field."""
        if isinstance(obj.drug_names, list):
            return ', '.join(obj.drug_names[:5])  # Show first 5
        return str(obj.drug_names)
    get_drug_names_display.short_description = 'Drugs Scanned'


# ============================================
# NOTIFICATION ADMIN
# ============================================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin interface for user notifications.
    Allows manual creation of notifications for testing.
    """
    list_display = ('user', 'title', 'is_read', 'created_at')
    list_filter = ('is_read', 'type', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    fields = ('user', 'title', 'message', 'type', 'is_read', 'created_at')


# ============================================
# ADMIN SITE BRANDING
# ============================================
# Note: Branding is now handled by Jazzmin in settings.py
# These are kept as fallback if Jazzmin is not installed
admin.site.site_header = "SafeMedsAI Admin"
admin.site.site_title = "SafeMedsAI Admin Portal"
admin.site.index_title = "Welcome to SafeMedsAI Administration"
