import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from django_email_learning.models import FromEmailType
from django_email_learning.services.email_sender_service import email_sender_service


def _enable_domain_wide(settings, domain="learn.example.com"):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "DOMAIN_WIDE_EMAIL": {"ENABLED": True, "DOMAIN": domain},
    }


def _disable_domain_wide(settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "DOMAIN_WIDE_EMAIL": {"ENABLED": False, "DOMAIN": None},
    }


def test_public_url_is_none_when_course_disabled(course):
    course.enabled = False
    course.is_public = True
    course.save()

    assert course.public_url is None


def test_public_url_is_none_when_course_not_public(course):
    course.enabled = True
    course.is_public = False
    course.save()

    assert course.public_url is None


def test_public_url_is_none_when_organization_not_public(course):
    course.enabled = True
    course.is_public = True
    course.save()
    course.organization.is_public = False
    course.organization.save()

    assert course.public_url is None


def test_public_url_returns_absolute_url_when_publicly_reachable(course, settings):
    course.enabled = True
    course.is_public = True
    course.save()

    expected_path = reverse(
        "django_email_learning:public:course_view",
        kwargs={"organization_id": course.organization_id, "course_slug": course.slug},
    )
    assert course.public_url == f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{expected_path}"


def test_enrollments_count_property(course, enrollments_factory):
    enrollments_factory(course=course, status="unverified", count=3)
    enrollments_factory(course=course, status="active", count=5)
    enrollments_factory(course=course, status="completed", count=2)
    enrollments_factory(course=course, status="deactivated", count=1)

    counts = course.enrollments_count
    assert counts["unverified"] == 3
    assert counts["active"] == 5
    assert counts["completed"] == 2
    assert counts["deactivated"] == 1
    assert counts["total"] == 11


def test_from_email_type_defaults_to_platform(course):
    assert course.from_email_type == FromEmailType.PLATFORM_DEFAULT


def test_from_email_for_course_uses_platform_default_by_default(course, settings):
    assert email_sender_service.from_email_for_course(course) == email_sender_service.from_email


def test_from_email_for_course_uses_organization_address_when_enabled(course, settings):
    _enable_domain_wide(settings)
    course.from_email_type = FromEmailType.ORGANIZATION
    course.save()

    expected_local = f"{course.organization.email_local_part}@learn.example.com"
    resolved = email_sender_service.from_email_for_course(course)
    assert course.organization.name in resolved
    assert expected_local in resolved


def test_from_email_for_course_falls_back_when_domain_wide_disabled(course, settings):
    _enable_domain_wide(settings)
    course.from_email_type = FromEmailType.ORGANIZATION
    course.save()

    _disable_domain_wide(settings)
    assert email_sender_service.from_email_for_course(course) == email_sender_service.from_email


def test_clean_blocks_switching_to_organization_when_disabled(course, settings):
    _disable_domain_wide(settings)
    course.from_email_type = FromEmailType.ORGANIZATION
    with pytest.raises(ValidationError):
        course.save()


def test_clean_allows_saving_existing_organization_course_when_disabled(course, settings):
    _enable_domain_wide(settings)
    course.from_email_type = FromEmailType.ORGANIZATION
    course.save()

    _disable_domain_wide(settings)
    course.title = "Renamed while domain-wide disabled"
    course.save()  # must not raise
    course.refresh_from_db()
    assert course.from_email_type == FromEmailType.ORGANIZATION
