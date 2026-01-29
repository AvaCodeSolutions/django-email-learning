from django.apps import AppConfig
from django.core import checks


PLATFORM_ADMIN_GROUP_NAME = "Platform Admin"


def check_site_base_url_config(app_configs, **kwargs):  # type: ignore[no-untyped-def]
    errors = []
    from django.conf import settings

    if (
        not hasattr(settings, "DJANGO_EMAIL_LEARNING")
        or "SITE_BASE_URL" not in settings.DJANGO_EMAIL_LEARNING
    ):
        errors.append(
            checks.Error(
                "DJANGO_EMAIL_LEARNING['SITE_BASE_URL'] is not set in settings.",
                hint="Please set DJANGO_EMAIL_LEARNING['SITE_BASE_URL'] to the base URL of your site.",
                id="django_email_learning.E001",
            )
        )
    if (
        not hasattr(settings, "DJANGO_EMAIL_LEARNING")
        or "ENCRYPTION_SECRET_KEY" not in settings.DJANGO_EMAIL_LEARNING
    ):
        errors.append(
            checks.Error(
                "DJANGO_EMAIL_LEARNING['ENCRYPTION_SECRET_KEY'] is not set in settings.",
                hint="Please set DJANGO_EMAIL_LEARNING['ENCRYPTION_SECRET_KEY'] to a long, random string.",
                id="django_email_learning.E002",
            )
        )
    return errors


class EmailLearningConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_email_learning"
    verbose_name = "Email Learning"

    def ready(self) -> None:
        import django_email_learning.signals  # noqa

        checks.register(check_site_base_url_config)
