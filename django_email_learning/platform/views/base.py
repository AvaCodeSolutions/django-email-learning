import logging
from typing import Any, Dict

from django.apps import apps
from django.conf import settings
from django.conf.global_settings import LANGUAGES
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import get_language, get_language_info, gettext as _
from django.views.generic import TemplateView

from django_email_learning.models import (
    Organization,
    OrganizationUser,
)
from django_email_learning.platform.features import PlatformFeature
from django_email_learning.services import (
    jwt_service,  # noqa: F401 — re-exported for views that import from here
)

DJANGO_EMAIL_LEARNING_SETTINGS: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
AI_CONFIGURATIONS: dict = DJANGO_EMAIL_LEARNING_SETTINGS.get("AI", {})
QUIZ_DEFAULTS: dict = DJANGO_EMAIL_LEARNING_SETTINGS.get("QUIZ_DEFAULTS", {})


@method_decorator(login_required, name="dispatch")
class BasePlatformView(TemplateView):
    """Base view for all platform views with shared context"""

    def get_context_data(self, **kwargs) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)
        context.update(self.get_shared_context())
        return context

    def get_shared_context(self) -> Dict[str, Any]:
        """Get shared context for all platform views"""
        active_organization_id = self.get_or_set_active_organization()
        if self.request.user.is_superuser:
            role = "admin"
        else:
            role = OrganizationUser.objects.get(  # type: ignore[misc]
                user=self.request.user,
                organization_id=active_organization_id,
            ).role

        current_lang_code = get_language()
        lang_info = get_language_info(current_lang_code)

        return {
            "appContext": {
                "apiBaseUrl": reverse("django_email_learning:api_platform:root")[:-1],
                "platformBaseUrl": reverse("django_email_learning:platform:root")[:-1],
                "analyticsBaseUrl": {
                    "base": (
                        reverse(
                            "django_email_learning:api_analytics:enrollments_over_time",
                            kwargs={"organization_id": active_organization_id},
                        ).rsplit("/enrollments", 1)[0]
                    ),
                    "orgId": active_organization_id,
                },
                "sidebarCustomComponent": {
                    "scriptUrl": DJANGO_EMAIL_LEARNING_SETTINGS.get("SIDEBAR", {})
                    .get("CUSTOM_COMPONENT", {})
                    .get("SCRIPT_URL"),
                    "componentTag": DJANGO_EMAIL_LEARNING_SETTINGS.get("SIDEBAR", {})
                    .get("CUSTOM_COMPONENT", {})
                    .get("COMPONENT_TAG"),
                    "styleUrl": DJANGO_EMAIL_LEARNING_SETTINGS.get("SIDEBAR", {})
                    .get("CUSTOM_COMPONENT", {})
                    .get("STYLE_URL"),
                },
                "navbarCustomComponents": [],
                "userRole": role,
                "direction": "rtl" if lang_info["bidi"] else "ltr",
                "isPlatformAdmin": (
                    self.request.user.is_superuser
                    or (
                        self.request.user.is_authenticated
                        and getattr(self.request.user, "has_platform_admin_role", False)
                    )
                ),
                "isInstructor": (
                    self.request.user.is_superuser
                    or (
                        OrganizationUser.objects.filter(
                            user=self.request.user,
                            organization_id=active_organization_id,
                            role="instructor",
                        ).exists()  # type: ignore[misc]
                    )
                ),
                "aiTextEditingModel": AI_CONFIGURATIONS.get("TEXT_EDITING_MODEL"),
                "availableFeatures": [f.value for f in self.get_available_features()],
                "customLogo": {
                    "horizontalLight": DJANGO_EMAIL_LEARNING_SETTINGS.get("LOGO", {})
                    .get("HORIZONTAL_LOCKUP", {})
                    .get("LIGHT_BACKGROUND"),
                    "horizontalDark": DJANGO_EMAIL_LEARNING_SETTINGS.get("LOGO", {})
                    .get("HORIZONTAL_LOCKUP", {})
                    .get("DARK_BACKGROUND"),
                    "verticalLight": DJANGO_EMAIL_LEARNING_SETTINGS.get("LOGO", {})
                    .get("VERTICAL_LOCKUP", {})
                    .get("LIGHT_BACKGROUND"),
                    "verticalDark": DJANGO_EMAIL_LEARNING_SETTINGS.get("LOGO", {})
                    .get("VERTICAL_LOCKUP", {})
                    .get("DARK_BACKGROUND"),
                }
                if DJANGO_EMAIL_LEARNING_SETTINGS.get("LOGO")
                else None,
                "isOrganizationAdmin": (
                    self.request.user.is_superuser
                    or (
                        OrganizationUser.objects.filter(
                            user=self.request.user,
                            organization_id=active_organization_id,
                            role="admin",
                        ).exists()  # type: ignore[misc]
                    )
                ),
                "localeMessages": {
                    "organizations": _("Organizations"),
                    "course_management": _("Course Management"),
                    "learners": _("Learners"),
                    "analytics": _("Analytics"),
                    "settings": _("Settings"),
                    "api_keys": _("API Keys"),
                    "content_delivery_job": _("Content Delivery Job"),
                    "last_run": _("Last Run:"),
                    "never_run": _("This job has never been executed."),
                    "content_delivery_tooltip": _(
                        "This job should run on a regular schedule to ensure timely content delivery."
                        " Configure a cron job or cloud scheduler to execute it at appropriate intervals,"
                        " such as every five minutes."
                    ),
                }
                | self.get_locale_messages(),
                "languageOptions": [{"value": code, "label": name} for code, name in LANGUAGES],
            },
            "activeOrganizationId": active_organization_id,
            "favicon": DJANGO_EMAIL_LEARNING_SETTINGS.get("FAVICON"),
        }

    def get_available_features(self) -> set[PlatformFeature]:
        features: set[PlatformFeature] = {PlatformFeature.CREATE_COURSE}
        if AI_CONFIGURATIONS.get("TEXT_EDITING_MODEL"):
            features.add(PlatformFeature.AI_EDIT)
        if DJANGO_EMAIL_LEARNING_SETTINGS.get("GOOGLE_OAUTH", {}).get("CLIENT_ID") and apps.is_installed(
            "django_email_learning.oauth_integrations"
        ):
            features.add(PlatformFeature.GOOGLE_WORKSPACE_ENROLL)
        if getattr(settings, "DJANGO_EMAIL_LEARNING", {}).get("NEWSLETTERS"):
            features.add(PlatformFeature.NEWSLETTERS)
            features.add(PlatformFeature.CREATE_NEWSLETTER)
        return features

    def get_locale_messages(self) -> Dict[str, str]:
        return {}

    def get_or_set_active_organization(self) -> str:
        org = self.request.session.get("active_organization_id")
        if org:
            return org

        member = self.request.user.memberships.first()  # type: ignore[union-attr]
        logging.debug(f"User memberships: {member}")
        if member:
            org = member.organization
        elif self.request.user.is_superuser:
            org = Organization.objects.first()

        if org:
            logging.debug(f"Active organization: {org}")
            self.request.session["active_organization_id"] = str(org.id)
            return str(org.id)

        raise Exception("No active organization found for the user.")
