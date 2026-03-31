from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
from django.db.models import Prefetch
from django_email_learning.models import Organization, Course
from django.utils.translation import get_language_info, get_language
from django.http import Http404
from django.urls import reverse
from django.utils.translation import gettext as _
from django.conf import settings
from django_email_learning.public.serializers import (
    OrganizationSerializer,
    PublicCourseSerializer,
)


def json_ld_from(
    courses: list[PublicCourseSerializer], organization: Organization
) -> dict:
    course_list = []
    for course in courses:
        course_data = {
            "@type": "Course",
            "name": course.title,
            "description": course.description,
            "inLanguage": course.language,
            "provider": {
                "@type": "Organization",
                "name": organization.name,
            },
        }
        if course.image:
            course_data["image"] = course.image
        course_list.append(course_data)
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "itemListElement": course_list,
    }


@method_decorator(ensure_csrf_cookie, name="dispatch")
class OrganizationView(TemplateView):
    template_name = "public/organization.html"

    def get_context_data(self, **kwargs) -> dict:  # type: ignore[no-untyped-def]
        get_token(self.request)  # Ensure CSRF token is set in cookies
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
                course_lang_info = get_language_info(course.language)
                course_data = PublicCourseSerializer(
                    id=course.id,
                    title=course.title,
                    slug=course.slug,
                    description=course.description,
                    image=self.request.build_absolute_uri(course.image.url)
                    if course.image
                    else None,
                    imap_email=course.imap_connection.email
                    if course.imap_connection
                    else None,
                    language=course.language,
                    is_rtl=course_lang_info["bidi"],
                )
                courses.append(course_data)
            organization_data = OrganizationSerializer(
                id=organization.id,
                name=organization.name,
                logo_url=organization.logo.url if organization.logo else None,
                description=organization.description,
                courses=courses,
                public_url=organization.public_url,
            )
            enroll_api_path = reverse("django_email_learning:api_public:enroll")
            current_lang_code = get_language()
            lang_info = get_language_info(current_lang_code)
            context["appContext"] = {
                "organization": organization_data.model_dump(),
                "enrollApiUrl": f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{enroll_api_path}",
                "direction": "rtl" if lang_info["bidi"] else "ltr",
                "localeMessages": {
                    "courses": _("Courses"),
                    "enroll_now": _("Enroll Now"),
                    "enrol_for_course": _("Enroll for COURSE_NAME"),
                    "email": _("email"),
                    "cancel": _("Cancel"),
                    "submit": _("Submit"),
                    "enrollment_success": _("You are enrolled in this course."),
                    "enrollment_failed": _("Enrollment failed. Please try again."),
                    "no_courses_available": _("No courses available."),
                    "email_required": _("Email is required"),
                    "email_invalid": _("Please enter a valid email address"),
                    "course_language": _("Course language"),
                    "in_app_browser_or_disabled_cookies": _(
                        "It seems you are using an in-app browser or have disabled cookies. Please open this link in a regular browser and ensure cookies are enabled to enroll in courses."
                    ),
                    "continue": _("Continue"),
                },
            }
            context["organization_name"] = organization.name
            context["organization_description"] = organization.description
            context["organization_logo_url"] = (
                self.request.build_absolute_uri(organization.logo.url)
                if organization.logo
                else None
            )

            if len(courses) > 0:
                context["json_ld"] = json_ld_from(courses, organization)
            context["page_title"] = organization.name
            return context

        # If organization not found, raise 404
        raise Http404(_("Organization does not exist"))


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CourseView(TemplateView):
    template_name = "public/course.html"

    def get_context_data(self, **kwargs) -> dict:  # type: ignore[no-untyped-def]
        get_token(self.request)  # Ensure CSRF token is set in cookies
        course_slug: str = kwargs.get("course_slug")  # type: ignore[assignment]
        organization_id: int = kwargs.get("organization_id")  # type: ignore[assignment]
        context = super().get_context_data(**kwargs)
        try:
            course = Course.objects.select_related("organization").get(
                slug=course_slug, organization__id=organization_id, enabled=True
            )
        except Course.DoesNotExist:
            raise Http404(_("Course does not exist"))

        course_lang_info = get_language_info(course.language)
        course_data = PublicCourseSerializer(
            id=course.id,
            title=course.title,
            slug=course.slug,
            description=course.description,
            image=self.request.build_absolute_uri(course.image.url)
            if course.image
            else None,
            imap_email=None,
            language=course.language,
            is_rtl=course_lang_info["bidi"],
            lessons=[
                content.lesson.title  # type: ignore[union-attr]
                for content in course.coursecontent_set.filter(
                    lesson__isnull=False
                ).order_by("priority")
            ],
        )
        organization_data = OrganizationSerializer(
            id=course.organization.id,
            name=course.organization.name,
            logo_url=self.request.build_absolute_uri(course.organization.logo.url)
            if course.organization.logo
            else None,
            description=course.organization.description,
            public_url=course.organization.public_url,
        )
        enroll_api_path = reverse("django_email_learning:api_public:enroll")
        current_lang_code = get_language()
        lang_info = get_language_info(current_lang_code)
        context["appContext"] = {
            "course": course_data.model_dump(),
            "organization": organization_data.model_dump(),
            "enrollApiUrl": f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{enroll_api_path}",
            "direction": "rtl" if lang_info["bidi"] else "ltr",
            "localeMessages": {
                "enroll_now": _("Enroll Now"),
                "enrol_for_course": _("Enroll for COURSE_NAME"),
                "email": _("email"),
                "cancel": _("Cancel"),
                "submit": _("Submit"),
                "enrollment_success": _("You are enrolled in this course."),
                "enrollment_failed": _("Enrollment failed. Please try again."),
                "email_required": _("Email is required"),
                "email_invalid": _("Please enter a valid email address"),
                "course_language": _("Course language"),
                "topics_covered": _(
                    "Here is the list of topics covered in this course:"
                ),
                "provided_by": _("Provided by ORGANIZATION_NAME"),
                "in_app_browser_or_disabled_cookies": _(
                    "It seems you are using an in-app browser or have disabled cookies. Please open this link in a regular browser and ensure cookies are enabled to enroll in courses."
                ),
                "continue": _("Continue"),
            },
        }
        context["course_title"] = course.title
        context["course_description"] = course.description
        context["course_image_url"] = (
            self.request.build_absolute_uri(course.image.url) if course.image else None
        )
        context["organization_name"] = course.organization.name
        context["organization_description"] = course.organization.description
        context["organization_logo_url"] = (
            self.request.build_absolute_uri(course.organization.logo.url)
            if course.organization.logo
            else None
        )
        context["page_title"] = course.title
        return context
