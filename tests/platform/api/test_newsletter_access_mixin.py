import json

from django.http import JsonResponse
from django.test import RequestFactory
from django.views import View

from django_email_learning.platform.api.newsletter_access_mixin import NewsletterAccessMixin


class _AllowedView(NewsletterAccessMixin, View):
    def get(self, request, *args, **kwargs) -> JsonResponse:
        return JsonResponse({"ok": True}, status=200)


class _DeniedView(NewsletterAccessMixin, View):
    def newsletter_access_allowed(self, request, *args, **kwargs) -> bool:
        return False

    def get(self, request, *args, **kwargs) -> JsonResponse:
        return JsonResponse({"ok": True}, status=200)


def test_newsletter_access_allowed_by_default():
    request = RequestFactory().get("/")
    response = _AllowedView.as_view()(request)
    assert response.status_code == 200


def test_newsletter_access_denied_returns_403():
    request = RequestFactory().get("/")
    response = _DeniedView.as_view()(request)
    assert response.status_code == 403
    assert json.loads(response.content) == {"error": "Forbidden"}
