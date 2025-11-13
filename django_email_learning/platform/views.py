import logging
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse
from django_email_learning.models import Organization
from django_email_learning.decorators import is_platform_admin
from typing import Dict, Any


@method_decorator(login_required, name="dispatch")
class BasePlatformView(TemplateView):
    """Base view for all platform views with shared context"""

    def get_context_data(self, **kwargs) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)
        context.update(self.get_shared_context())
        return context

    def get_shared_context(self) -> Dict[str, Any]:
        """Get shared context for all platform views"""
        return {
            "api_base_url": reverse("django_email_learning:api:root")[:-1],
            "platform_base_url": reverse("django_email_learning:platform:root")[:-1],
            "active_organization_id": self.get_or_set_active_organization(),
            "is_platform_admin": (
                self.request.user.is_superuser
                or (
                    self.request.user.is_authenticated
                    and getattr(self.request.user, "has_platform_admin_role", False)
                )
            ),
        }

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


@method_decorator(login_required, name="dispatch")
class Courses(BasePlatformView):
    template_name = "platform/courses.html"

    def get_context_data(self, **kwargs) -> dict:  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Courses"
        return context


@method_decorator(login_required, name="dispatch")
@method_decorator(is_platform_admin(), name="dispatch")
class Organizations(BasePlatformView):
    template_name = "platform/organizations.html"

    def get_context_data(self, **kwargs):  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Organizations"
        return context
