from django.apps import AppConfig


class DrugsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'drugs'
    
    def ready(self):
        """
        Import signals when the app is ready.
        This ensures signals are connected when Django starts.
        """
        import drugs.signals  # noqa