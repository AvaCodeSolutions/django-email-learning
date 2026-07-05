from django.urls import reverse


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
