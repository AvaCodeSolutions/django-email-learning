from typing import Dict, List

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _

from django_email_learning.models import (
    Course,
    Learner,
    Newsletter,
    NewsletterSubscriber,
    Organization,
    OrganizationUser,
)
from django_email_learning.platform.dashboard_sections import DashboardSection
from django_email_learning.platform.features import PlatformFeature
from django_email_learning.platform.views.base import BasePlatformView

DEFAULT_DASHBOARD_SECTIONS = [
    DashboardSection.SETUP_PROGRESS,
    DashboardSection.OVERVIEW,
    DashboardSection.QUICK_ACTIONS,
    DashboardSection.SPONSOR,
]

CUSTOM_COMPONENT_PREFIX = f"{DashboardSection.CUSTOM_COMPONENT.value}:"


@method_decorator(login_required, name="dispatch")
class Dashboard(BasePlatformView):
    template_name = "platform/dashboard.html"

    def get_dashboard_sections(self) -> List[str]:
        """
        Ordered list of section keys to render below the always-first Welcome
        section. Built-in sections are plain keys ("overview", "quick_actions", …);
        a named custom slot is "custom_component:<name>", resolved against
        get_dashboard_custom_components(). Override DASHBOARD.SECTIONS in settings,
        or override this method, to reorder, drop, or add sections.
        """
        configured = getattr(settings, "DJANGO_EMAIL_LEARNING", {}).get("DASHBOARD", {}).get("SECTIONS")
        if configured:
            return list(configured)
        return [section.value for section in DEFAULT_DASHBOARD_SECTIONS]

    def get_dashboard_custom_components(self) -> Dict[str, Dict[str, str]]:
        """
        Name -> {componentTag, scriptUrl, styleUrl} for every custom dashboard
        component available to reference from get_dashboard_sections(), using the
        same shape as SIDEBAR.CUSTOM_COMPONENT. Configure via DASHBOARD.CUSTOM_COMPONENTS
        in settings, or override this method.
        """
        return getattr(settings, "DJANGO_EMAIL_LEARNING", {}).get("DASHBOARD", {}).get("CUSTOM_COMPONENTS", {})

    def get_context_data(self, **kwargs) -> Dict:  # type: ignore[no-untyped-def]
        context = super().get_context_data(**kwargs)
        context["page_title"] = _("Dashboard")

        sections = self.get_dashboard_sections()
        referenced_custom_component_names = {
            section[len(CUSTOM_COMPONENT_PREFIX) :]
            for section in sections
            if section.startswith(CUSTOM_COMPONENT_PREFIX)
        }
        available_custom_components = self.get_dashboard_custom_components()
        context["appContext"]["dashboardSections"] = sections
        context["appContext"]["dashboardCustomComponents"] = {
            name: available_custom_components[name]
            for name in referenced_custom_component_names
            if name in available_custom_components
        }

        organization_id = self.get_or_set_active_organization()
        organization = Organization.objects.get(id=organization_id)
        active_org_user = (
            None
            if self.request.user.is_superuser
            else OrganizationUser.objects.filter(  # type: ignore[misc]
                user=self.request.user, organization_id=organization_id
            ).first()
        )
        newsletters_enabled = PlatformFeature.NEWSLETTERS in self.get_available_features()

        newsletter_subscribers = 0
        if newsletters_enabled:
            newsletter_subscribers = NewsletterSubscriber.objects.filter(
                newsletter__organization_id=organization_id,
                confirmed_at__isnull=False,
            ).count()

        context["appContext"]["activeOrganizationName"] = organization.name
        context["appContext"]["greetingName"] = active_org_user.display_name if active_org_user else None
        context["appContext"]["organizationIsPublic"] = organization.is_public
        context["appContext"]["organizationPublicUrl"] = organization.public_url
        context["appContext"]["dashboardSetup"] = {
            "hasCourse": Course.objects.filter(organization_id=organization_id).exists(),
            "hasTeam": OrganizationUser.objects.filter(organization_id=organization_id).count() > 1,
            "profileComplete": bool(
                organization.description and organization.logo and organization.social_links.exists()
            ),
            "newsletterConfigured": (
                newsletters_enabled and Newsletter.objects.filter(organization_id=organization_id).exists()
            ),
        }
        context["appContext"]["dashboardStats"] = {
            "activeCourses": Course.objects.filter(organization_id=organization_id, enabled=True).count(),
            "enrolledLearners": Learner.objects.filter(organization_id=organization_id).count(),
            "newsletterSubscribers": newsletter_subscribers,
        }
        return context

    def get_locale_messages(self) -> Dict[str, str]:
        return {
            "welcome_back": _("Welcome back"),
            "welcome_back_name": _("Welcome back, NAME"),
            "dashboard_subtitle": _("Here's what's happening at ORGANIZATION_NAME."),
            "setup_checklist_title": _("Finish setting up your organization"),
            "setup_progress": _("DONE of TOTAL done"),
            "setup_course_title": _("Create your first course"),
            "setup_course_description": _("Publish a course so learners can start enrolling."),
            "setup_course_cta": _("Create course"),
            "setup_team_title": _("Invite your team"),
            "setup_team_description": _("Add instructors or co-admins to help manage courses and learners."),
            "setup_team_cta": _("Invite people"),
            "setup_profile_title": _("Complete your organization profile"),
            "setup_profile_description": _("Add a logo and social links so learners recognize you."),
            "setup_profile_cta": _("Edit profile"),
            "organization_profile_public_notice": _("Your organization profile page is public."),
            "organization_profile_public_link_label": _("View public page"),
            "setup_newsletter_title": _("Set up your newsletter"),
            "setup_newsletter_description": _("Send progress updates and announcements to enrolled learners."),
            "setup_newsletter_cta": _("Set up"),
            "overview_title": _("Overview"),
            "stat_active_courses": _("Active courses"),
            "stat_enrolled_learners": _("Enrolled learners"),
            "stat_newsletter_subscribers": _("Newsletter subscribers"),
            "stat_content_delivery_health": _("Content delivery health"),
            "content_delivery_healthy": _("Steady"),
            "content_delivery_warning": _("Needs attention"),
            "content_delivery_critical": _("Not running"),
            "quick_actions_title": _("Quick actions"),
            "action_add_course_title": _("Add a course"),
            "action_add_course_description": _("Start a new course from scratch or duplicate an existing one."),
            "action_add_course_cta": _("Create course"),
            "action_write_newsletter_title": _("Write a newsletter"),
            "action_write_newsletter_description": _("Draft an update to send to your subscribed learners."),
            "action_write_newsletter_cta": _("Open newsletter"),
            "action_view_analytics_title": _("View analytics"),
            "action_view_analytics_description": _("See enrollment and engagement trends across your courses."),
            "action_view_analytics_cta": _("Open analytics"),
            "sponsor_section_title": _("Sponsor"),
            "sponsor_title": _("Enjoying Django Email Learning?"),
            "sponsor_description": _(
                "If this project is useful to you, consider sponsoring its development or leaving a star "
                "on GitHub. Both help a lot."
            ),
            "sponsor_cta": _("Sponsor Django Email Learning"),
            "sponsor_star_cta": _("Star on GitHub"),
            "sponsor_remove_note": _("You can remove this section anytime via DASHBOARD.SECTIONS in your settings."),
            "sponsor_docs_link_label": _("see the docs"),
            "sponsor_dismiss_label": _("Dismiss"),
        }
