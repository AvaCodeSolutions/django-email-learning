from django.apps import AppConfig


class EmailLearningConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_email_learning"
    verbose_name = "Email Learning"

    def ready(self) -> None:
        import django_email_learning.signals  # noqa
