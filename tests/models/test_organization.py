import pytest
from django.core.exceptions import ValidationError
from django.db import transaction

from django_email_learning.models import Course, Enrollment, EnrollmentStatus, Learner, Organization


def custom_learners_cap_resolver(organization: Organization) -> int:
    return 7 if organization.name == "My Organization" else 0


def test_get_learners_cap_defaults_to_unlimited(db, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "LEARNERS": {}}
    organization = Organization.objects.get(id=1)
    assert organization.get_learners_cap() == 0


def test_get_learners_cap_reads_settings(db, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {"MAX_LEARNERS_PER_ORGANIZATION": 3},
    }
    organization = Organization.objects.get(id=1)
    assert organization.get_learners_cap() == 3


def test_can_enroll_learner_unlimited_by_default(db):
    organization = Organization.objects.get(id=1)
    assert organization.can_enroll_learner() is True


def test_can_enroll_learner_false_when_cap_reached(db, settings, course):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {"MAX_LEARNERS_PER_ORGANIZATION": 1},
    }
    organization = Organization.objects.get(id=1)
    learner = Learner.objects.create(email="learner@example.com", organization=organization)
    Enrollment.objects.create(learner=learner, course=course, status=EnrollmentStatus.ACTIVE)
    assert organization.can_enroll_learner() is False


def test_can_enroll_learner_true_when_under_cap(db, settings, course):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {"MAX_LEARNERS_PER_ORGANIZATION": 2},
    }
    organization = Organization.objects.get(id=1)
    learner = Learner.objects.create(email="learner@example.com", organization=organization)
    Enrollment.objects.create(learner=learner, course=course, status=EnrollmentStatus.ACTIVE)
    assert organization.can_enroll_learner() is True


def test_can_enroll_learner_ignores_learners_without_active_enrollment(db, settings, course):
    """
    Learners with no enrollment, or only non-active enrollments, shouldn't
    count against the cap.
    """
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {"MAX_LEARNERS_PER_ORGANIZATION": 1},
    }
    organization = Organization.objects.get(id=1)
    Learner.objects.create(email="no-enrollment@example.com", organization=organization)

    unverified_learner = Learner.objects.create(email="unverified@example.com", organization=organization)
    Enrollment.objects.create(learner=unverified_learner, course=course, status=EnrollmentStatus.UNVERIFIED)

    completed_learner = Learner.objects.create(email="completed@example.com", organization=organization)
    Enrollment.objects.create(learner=completed_learner, course=course, status=EnrollmentStatus.COMPLETED)

    deactivated_learner = Learner.objects.create(email="deactivated@example.com", organization=organization)
    Enrollment.objects.create(
        learner=deactivated_learner,
        course=course,
        status=EnrollmentStatus.DEACTIVATED,
        deactivation_reason="canceled",
    )

    assert organization.can_enroll_learner() is True


def test_can_enroll_learner_counts_distinct_learners_not_enrollments(db, settings, course):
    """
    A single learner active in multiple courses should only count once
    against the cap. With a cap of 2, if the two enrollments were counted
    instead of the one distinct learner, this would incorrectly report the
    cap as reached.
    """
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {"MAX_LEARNERS_PER_ORGANIZATION": 2},
    }
    organization = Organization.objects.get(id=1)
    second_course = Course.objects.create(
        title="Second Course",
        slug="second-course",
        description="Another course in the same organization.",
        organization=organization,
    )
    learner = Learner.objects.create(email="learner@example.com", organization=organization)
    Enrollment.objects.create(learner=learner, course=course, status=EnrollmentStatus.ACTIVE)
    Enrollment.objects.create(learner=learner, course=second_course, status=EnrollmentStatus.ACTIVE)

    assert organization.can_enroll_learner() is True


def test_get_learners_cap_uses_resolver_when_configured(db, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {
            "MAX_LEARNERS_PER_ORGANIZATION": 500,
            "LEARNERS_CAP_RESOLVER": "tests.models.test_organization.custom_learners_cap_resolver",
        },
    }
    organization = Organization.objects.get(id=1)
    assert organization.get_learners_cap() == 7


def test_get_learners_cap_resolver_receives_the_organization(db, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {"LEARNERS_CAP_RESOLVER": "tests.models.test_organization.custom_learners_cap_resolver"},
    }
    other_org = Organization.objects.create(name="Other Org")
    assert other_org.get_learners_cap() == 0


def test_name_rejects_url(db):
    with pytest.raises(ValidationError):
        Organization.objects.create(name="Spam at www.spam.example")


def test_name_rejects_newline(db):
    with pytest.raises(ValidationError):
        Organization.objects.create(name="Acme\nInc")


def test_name_rejects_value_over_60_characters(db):
    with pytest.raises(ValidationError):
        Organization.objects.create(name="A" * 61)


def test_name_accepts_ordinary_value_at_the_limit(db):
    organization = Organization.objects.create(name="A" * 60)
    assert organization.pk is not None


def test_name_does_not_have_to_be_unique(db):
    first = Organization.objects.create(name="Acme Consulting")
    second = Organization.objects.create(name="Acme Consulting")

    assert first.id != second.id
    assert Organization.objects.filter(name="Acme Consulting").count() == 2


def test_str_includes_the_id_to_disambiguate_same_named_organizations(db):
    organization = Organization.objects.create(name="Acme Consulting")

    assert str(organization) == f"Acme Consulting (#{organization.id})"


def test_email_local_part_uses_slug_and_id(db):
    organization = Organization.objects.create(name="Acme Consulting")
    assert organization.email_local_part == f"acme-consulting-{organization.id}"


def test_email_local_part_falls_back_to_org_id_for_non_ascii_name(db):
    organization = Organization.objects.create(name="日本語")
    assert organization.email_local_part == f"org-{organization.id}"


def test_domain_wide_from_email_is_empty_without_domain(db, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "DOMAIN_WIDE_EMAIL": {}}
    organization = Organization.objects.create(name="Acme Consulting")
    assert organization.domain_wide_from_email == ""


def test_domain_wide_from_email_builds_address_when_domain_set(db, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "DOMAIN_WIDE_EMAIL": {"ENABLED": False, "DOMAIN": "learn.example.com"},
    }
    organization = Organization.objects.create(name="Acme Consulting")
    # built from DOMAIN alone; the ENABLED switch is applied by callers
    assert organization.domain_wide_from_email == (
        f"Acme Consulting <acme-consulting-{organization.id}@learn.example.com>"
    )


def test_generate_embed_token_returns_distinct_values(db):
    assert Organization.generate_embed_token() != Organization.generate_embed_token()


def test_embed_token_defaults_to_null(db):
    organization = Organization.objects.create(name="Fresh Org")
    assert organization.embed_token is None


def test_embed_token_must_be_unique(db):
    Organization.objects.create(name="Org A", embed_token="shared-token")
    organization_b = Organization.objects.create(name="Org B")
    organization_b.embed_token = "shared-token"

    with pytest.raises(ValidationError), transaction.atomic():
        organization_b.save(update_fields=["embed_token"])


def test_get_or_create_embed_token_generates_and_persists(db):
    organization = Organization.objects.create(name="Fresh Org")
    assert organization.embed_token is None

    token = organization.get_or_create_embed_token()

    assert token is not None
    organization.refresh_from_db()
    assert organization.embed_token == token


def test_get_or_create_embed_token_is_idempotent(db):
    organization = Organization.objects.create(name="Fresh Org")

    first = organization.get_or_create_embed_token()
    second = organization.get_or_create_embed_token()

    assert first == second
