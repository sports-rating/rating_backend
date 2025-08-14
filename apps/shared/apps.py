from django.apps import AppConfig


class SharedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.shared'

    def ready(self):
        from apps.shared.utils import signals
