from django.views.generic import TemplateView
from django.db.models import Prefetch
from django_email_learning.models import Organization, Course
from django.http import Http404
from django.urls import reverse
from django.utils.translation import gettext as _
from django.conf import settings
from django_email_learning.public.serializers import (
    OrganizationSerializer,
    PublicCourseSerializer,
)


class OrganizationView(TemplateView):
    template_name = "public/organization.html"

    def get_context_data(self, **kwargs) -> dict:  # type: ignore[no-untyped-def]
        organization_id: int = kwargs.get("organization_id")  # type: ignore[assignment]
        context = super().get_context_data(**kwargs)
        # Add any additional context if needed
        organization_details = Organization.objects.filter(
            id=organization_id
        ).prefetch_related(
            Prefetch(
                "course_set",
                queryset=Course.objects.filter(enabled=True),
                to_attr="courses",
            ),
        )
        if organization_details.exists():
            organization = organization_details.first()
            if not organization:
                raise Http404(_("Organization does not exist"))
            courses = []
            for course in organization.courses:
                course_data = PublicCourseSerializer(
                    id=course.id,
                    title=course.title,
                    slug=course.slug,
                    description=course.description,
                    imap_email=course.imap_connection.email
                    if course.imap_connection
                    else None,
                )
                courses.append(course_data)
            organization_data = OrganizationSerializer(
                id=organization.id,
                name=organization.name,
                logo_url=organization.logo.url if organization.logo else None,
                description=organization.description,
                courses=courses,
            )
            enroll_api_path = reverse("django_email_learning:api_public:enroll")
            context[
                "enroll_api_url"
            ] = f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{enroll_api_path}"
            context["organization_json"] = organization_data.model_dump_json()
            context["organization"] = organization_data.model_dump()
            context["page_title"] = organization.name
            return context

        # If organization not found, raise 404
        raise Http404(_("Organization does not exist"))
