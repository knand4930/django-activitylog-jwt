from django.apps import AppConfig


class ActivitylogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'activitylog'

    def ready(self):
        from activitylog.signals import (
            auth_signals,
            model_signals,
            request_signals,
            cors_signals,
        )