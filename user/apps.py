from django.apps import AppConfig
from django.db.models.signals import post_migrate


class UserConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "user"

    def ready(self):
        from cafe.util import create_initial_groups  # Import your signals module

        post_migrate.connect(create_initial_groups, sender=self)
