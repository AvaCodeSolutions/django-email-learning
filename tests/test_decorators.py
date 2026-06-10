import pytest
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, JsonResponse
from django.contrib.auth.models import User

from django_email_learning.decorators import accessible_for


def _make_view():
    @accessible_for(roles={"admin"})
    def my_view(request, **kwargs):
        return JsonResponse({"ok": True})

    return my_view


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
