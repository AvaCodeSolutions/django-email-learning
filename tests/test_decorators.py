import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, JsonResponse

from django_email_learning.decorators import accessible_for, is_an_organization_member
from django_email_learning.models import Organization, OrganizationUser


def _make_view():
    @accessible_for(roles={"admin"})
    def my_view(request, **kwargs):
        return JsonResponse({"ok": True})

    return my_view


def _make_org_member_view(**decorator_kwargs):
    @is_an_organization_member(**decorator_kwargs)
    def my_view(request, **kwargs):
        return JsonResponse({"ok": True})

    return my_view


def _make_request(user, active_organization_id=None):
    request = HttpRequest()
    request.user = user
    request.session = {} if active_organization_id is None else {"active_organization_id": active_organization_id}
    return request


def test_accessible_for_raises_if_organization_id_missing(db):
    """accessible_for must raise ImproperlyConfigured when organization_id is absent from URL kwargs."""
    view = _make_view()
    request = HttpRequest()
    request.user = User(username="testuser", is_superuser=True)

    with pytest.raises(ImproperlyConfigured, match="organization_id"):
        view(request)


def test_accessible_for_does_not_raise_when_organization_id_present(db):
    """accessible_for must not raise when organization_id is present in URL kwargs."""
    view = _make_view()
    request = HttpRequest()
    request.user = User(username="testuser", is_superuser=True)

    response = view(request, organization_id=1)

    assert response.status_code == 200


def test_is_an_organization_member_denies_when_organization_cannot_be_resolved(db):
    """No organization_id in kwargs, no resolver, no fallback: must fail closed, not skip the check."""
    user = User.objects.create(username="testuser")
    org = Organization.objects.create(name="Org")
    OrganizationUser.objects.create(user=user, organization=org, role="admin")
    view = _make_org_member_view()
    request = _make_request(user)

    response = view(request)

    assert response.status_code == 403


def test_is_an_organization_member_uses_resolve_org_id_callable(db):
    """resolve_org_id must be used to look up the org that owns the object in the URL."""
    user = User.objects.create(username="testuser")
    org = Organization.objects.create(name="Org")
    OrganizationUser.objects.create(user=user, organization=org, role="admin")
    view = _make_org_member_view(resolve_org_id=lambda request, kwargs: kwargs["owning_org_id"])
    request = _make_request(user)

    denied = view(request, owning_org_id=org.id + 999)
    allowed = view(request, owning_org_id=org.id)

    assert denied.status_code == 403
    assert allowed.status_code == 200


def test_is_an_organization_member_active_org_fallback_ignores_other_memberships(db):
    """allow_active_org_fallback must only ever consult the session, never any other membership."""
    user = User.objects.create(username="testuser")
    org = Organization.objects.create(name="Org")
    OrganizationUser.objects.create(user=user, organization=org, role="admin")
    view = _make_org_member_view(allow_active_org_fallback=True)

    no_session = view(_make_request(user))
    with_session = view(_make_request(user, active_organization_id=org.id))

    assert no_session.status_code == 403
    assert with_session.status_code == 200
