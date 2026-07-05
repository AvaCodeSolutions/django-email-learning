import json

from django.conf import settings
from django.db.models import Prefetch
from django.http import Http404
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import get_language, get_language_info, gettext as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

from django_email_learning.models import Course, Newsletter, Organization
from django_email_learning.public.serializers import (
    OrganizationSerializer,
    PublicCourseSerializer,
)


def get_terms_of_service_url() -> str | None:
    return settings.DJANGO_EMAIL_LEARNING.get("TERMS_OF_SERVICE_URL")  # type: ignore[return-value]


def get_organization_json_ld_links(organization: Organization) -> dict[str, object]:
    json_ld_links: dict[str, object] = {"url": organization.public_url}
    same_as: list[str] = []

    if organization.website:
        same_as.append(organization.website)

    if organization.linkedin_page:
        same_as.append(organization.linkedin_page)

    if organization.youtube_channel:
        same_as.append(organization.youtube_channel)

    if same_as:
        json_ld_links["sameAs"] = same_as

    return json_ld_links


def build_organization_courses_json_ld(courses: list[PublicCourseSerializer], organization: Organization) -> str:
    course_list = []
    for course in courses:
        course_data: dict[str, object] = {
            "@type": "Course",
            "name": course.title,
            "description": course.description,
            "inLanguage": course.language,
        }
        course_data["provider"] = {"@type": "Organization", "name": organization.name}

        course_data["provider"].update(get_organization_json_ld_links(organization))  # type: ignore[attr-defined]
        if course.image:
            course_data["image"] = course.image
        course_list.append(course_data)
    return json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "itemListElement": course_list,
        }
    )


def build_single_course_json_ld(  # type: ignore[no-untyped-def]
    course: Course,
    course_data: PublicCourseSerializer,
    request,
) -> str:
    course_json_ld: dict[str, object] = {
        "@context": "https://schema.org",
        "@type": "Course",
        "name": course.title,
        "description": course.description,
        "url": request.build_absolute_uri(),
        "inLanguage": course.language,
        "provider": {
            "@type": "Organization",
            "name": course.organization.name,
        },
    }

    course_json_ld["provider"].update(  # type: ignore[attr-defined]
        get_organization_json_ld_links(course.organization)
    )

    if course_data.image:
        course_json_ld["image"] = course_data.image

    if course.organization.logo:
        course_json_ld["provider"]["logo"] = request.build_absolute_uri(  # type: ignore[index]
            course.organization.logo.url
        )

    if course.organization.description:
        course_json_ld["provider"]["description"] = course.organization.description  # type: ignore[index]

    if course.target_audience:
        course_json_ld["audience"] = {
            "@type": "Audience",
            "audienceType": course.target_audience,
        }

    if course_data.lessons:
        course_json_ld["teaches"] = course_data.lessons

    return json.dumps(course_json_ld)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class OrganizationView(TemplateView):
    template_name = "public/organization.html"

    def get_max_subscribers(self) -> int:
        return (
            getattr(settings, "DJANGO_EMAIL_LEARNING", {})
            .get("NEWSLETTERS", {})
            .get("MAX_SUBSCRIBER_PER_NEWSLETTER", 500)
        )

    def get_context_data(self, **kwargs) -> dict:  # type: ignore[no-untyped-def]
        get_token(self.request)  # Ensure CSRF token is set in cookies
        organization_id: int = kwargs.get("organization_id")  # type: ignore[assignment]
        context = super().get_context_data(**kwargs)
        # Add any additional context if needed
        organization_details = Organization.objects.filter(
            id=organization_id,
            is_public=True,
        ).prefetch_related(
            Prefetch(
                "course_set",
                queryset=Course.objects.filter(enabled=True, is_public=True).select_related(
                    "imap_connection", "newsletter"
                ),
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
                    image=self.request.build_absolute_uri(course.image.url) if course.image else None,
                    imap_email=course.imap_connection.email if course.imap_connection else None,
                    language=course.language,
                    is_rtl=course_lang_info["bidi"],
                    newsletter_id=course.newsletter_id,
                    newsletter_title=course.newsletter.title if course.newsletter else None,
                )
                courses.append(course_data)
            organization_data = OrganizationSerializer(
                id=organization.id,
                name=organization.name,
                logo_url=organization.logo.url if organization.logo else None,
                description=organization.description,
                courses=courses,
                public_url=organization.public_url,
                website=organization.website,
                youtube_channel=organization.youtube_channel,
                linkedin_page=organization.linkedin_page,
            )
            enroll_api_path = reverse("django_email_learning:api_public:enroll")
            subscribe_api_path = reverse(
                "django_email_learning:api_public:newsletter_subscribe",
                kwargs={"organization_id": organization_id},
            )
            max_subscribers = self.get_max_subscribers()
            newsletters = [
                {"id": n.id, "title": n.title}
                for n in Newsletter.objects.filter(organization_id=organization_id)
                if n.subscribers.count() < max_subscribers
            ]
            current_lang_code = get_language()
            lang_info = get_language_info(current_lang_code)
            context["appContext"] = {
                "organization": organization_data.model_dump(),
                "enrollApiUrl": f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{enroll_api_path}",
                "newsletterSubscribeApiUrl": f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{subscribe_api_path}",
                "newsletters": newsletters,
                "direction": "rtl" if lang_info["bidi"] else "ltr",
                "termsOfServiceUrl": get_terms_of_service_url(),
                "localeMessages": {
                    "courses": _("Courses"),
                    "enroll_now": _("Enroll Now"),
                    "enrolled": _("Enrolled"),
                    "enrol_for_course": _("Enroll for COURSE_NAME"),
                    "email": _("email"),
                    "cancel": _("Cancel"),
                    "submit": _("Submit"),
                    "enrollment_success": _(
                        "We've sent a confirmation email to verify your enrollment."
                        " Please check your inbox and follow the link to complete the process."
                        " Don't see it? Check your Spam or Junk folder."
                    ),
                    "enrollment_failed": _("Enrollment failed. Please try again."),
                    "no_courses_available": _("No courses available."),
                    "email_required": _("Email is required"),
                    "email_invalid": _("Please enter a valid email address"),
                    "course_language": _("Course language"),
                    "in_app_browser_or_disabled_cookies": _(
                        "It seems you are using an in-app browser or have disabled cookies."
                        " Please open this link in a regular browser and ensure cookies are enabled"
                        " to enroll in courses."
                    ),
                    "continue": _("Continue"),
                    "linkedin_page": _("LinkedIn"),
                    "youtube_channel": _("YouTube"),
                    "website": _("Website"),
                    "terms_of_service_confirmation": _(
                        "By enrolling, you agree to our"
                        " <a href='TERMS_OF_SERVICE_URL' target='_blank'>Terms of Service</a>."
                    ),
                    "newsletters": _("Newsletters"),
                    "newsletter_subscribe_intro": _("Choose which updates you'd like to receive by email:"),
                    "newsletter_subscribe": _("Subscribe"),
                    "newsletter_subscribe_success": _("You have been successfully subscribed."),
                    "newsletter_subscribe_error": _("Subscription failed. Please try again."),
                    "newsletter_select_one": _("Please select at least one newsletter."),
                    "subscribe_to_newsletter": _("Subscribe to NEWSLETTER_TITLE"),
                },
            }
            context["organization_name"] = organization.name
            context["organization_description"] = organization.description
            context["organization_logo_url"] = (
                self.request.build_absolute_uri(organization.logo.url) if organization.logo else None
            )

            if len(courses) > 0:
                context["json_ld"] = build_organization_courses_json_ld(courses, organization)
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
                slug=course_slug,
                organization__id=organization_id,
                enabled=True,
                is_public=True,
                organization__is_public=True,
            )
        except Course.DoesNotExist:
            raise Http404(_("Course does not exist"))

        course_lang_info = get_language_info(course.language)
        course_data = PublicCourseSerializer(
            id=course.id,
            title=course.title,
            slug=course.slug,
            description=course.description,
            image=self.request.build_absolute_uri(course.image.url) if course.image else None,
            imap_email=None,
            language=course.language,
            is_rtl=course_lang_info["bidi"],
            target_audience=course.target_audience,
            external_references=[{"name": ref.name, "url": ref.url} for ref in course.external_references.all()]
            or None,
            lessons=[
                content.lesson.title  # type: ignore[union-attr]
                for content in course.coursecontent_set.filter(lesson__isnull=False).order_by("priority")
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
            website=course.organization.website,
            youtube_channel=course.organization.youtube_channel,
            linkedin_page=course.organization.linkedin_page,
        )
        enroll_api_path = reverse("django_email_learning:api_public:enroll")
        current_lang_code = get_language()
        lang_info = get_language_info(current_lang_code)
        context["appContext"] = {
            "course": course_data.model_dump(),
            "organization": organization_data.model_dump(),
            "enrollApiUrl": f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{enroll_api_path}",
            "direction": "rtl" if lang_info["bidi"] else "ltr",
            "termsOfServiceUrl": get_terms_of_service_url(),
            "localeMessages": {
                "enroll_now": _("Enroll Now"),
                "enrol_for_course": _("Enroll for COURSE_NAME"),
                "email": _("email"),
                "cancel": _("Cancel"),
                "submit": _("Submit"),
                "enrollment_success": _(
                    "We've sent a confirmation email to verify your enrollment."
                    " Please check your inbox and follow the link to complete the process."
                    " Don't see it? Check your Spam or Junk folder."
                ),
                "enrollment_failed": _("Enrollment failed. Please try again."),
                "email_required": _("Email is required"),
                "email_invalid": _("Please enter a valid email address"),
                "course_language": _("Course language"),
                "topics_covered": _("Here is the list of topics covered in this course:"),
                "provided_by": _("Provided by ORGANIZATION_NAME"),
                "in_app_browser_or_disabled_cookies": _(
                    "It seems you are using an in-app browser or have disabled cookies."
                    " Please open this link in a regular browser and ensure cookies are enabled"
                    " to enroll in courses."
                ),
                "continue": _("Continue"),
                "target_audience_title": _("Who is this course for?"),
                "external_references_title": _("External References"),
                "terms_of_service_confirmation": _(
                    "By enrolling, you agree to our"
                    " <a href='TERMS_OF_SERVICE_URL' target='_blank'>Terms of Service</a>."
                ),
            },
        }
        context["course_title"] = course.title
        context["course_description"] = course.description
        context["course_image_url"] = self.request.build_absolute_uri(course.image.url) if course.image else None
        context["json_ld"] = build_single_course_json_ld(
            course=course,
            course_data=course_data,
            request=self.request,
        )
        context["organization_name"] = course.organization.name
        context["organization_description"] = course.organization.description
        context["organization_logo_url"] = (
            self.request.build_absolute_uri(course.organization.logo.url) if course.organization.logo else None
        )
        context["page_title"] = course.title
        return context
