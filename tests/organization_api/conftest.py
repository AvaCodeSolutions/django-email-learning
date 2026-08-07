import pytest
from django.core.cache import cache
from django.test import Client

from django_email_learning.models import (
    ApiKey,
    ApiKeyScope,
    ApiKeyType,
    Course,
    Organization,
)

ALL_SCOPES = [
    ApiKeyScope.ENROLLMENTS_WRITE,
    ApiKeyScope.ENROLLMENTS_READ,
    ApiKeyScope.COURSES_READ,
]


@pytest.fixture(autouse=True)
def clear_rate_limit_cache():
    """Rate limiting is cache-backed and the counters outlive a test, so a
    later test would otherwise inherit an earlier one's budget."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture()
def api_client() -> Client:
    """A plain client. The root conftest's `client` is indirectly parametrized
    by role, which these key-authenticated endpoints have no use for.
    """
    return Client()


@pytest.fixture()
def enabled_course(db, course) -> Course:
    course.enabled = True
    course.save()
    return course


@pytest.fixture()
def other_organization(db) -> Organization:
    organization = Organization(name="Other Organization")
    organization.save()
    return organization


@pytest.fixture()
def other_organization_course(db, other_organization) -> Course:
    course = Course(
        title="Other Course",
        slug="other-course",
        organization=other_organization,
        enabled=True,
    )
    course.save()
    return course


def make_key(scopes, organization_id: int = 1) -> str:
    _, token = ApiKey.create(
        key_type=ApiKeyType.ORGANIZATION,
        name="Test key",
        organization_id=organization_id,
        scopes=list(scopes),
    )
    return token


@pytest.fixture()
def api_token(db) -> str:
    return make_key(ALL_SCOPES)


@pytest.fixture()
def auth(api_token):
    return {"HTTP_AUTHORIZATION": f"Bearer {api_token}"}
