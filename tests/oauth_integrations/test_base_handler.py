from django_email_learning.oauth_integrations.base_handler import BaseOAuthSessionHandler


class _DummyHandler(BaseOAuthSessionHandler):
    provider_and_purpose: str = "dummy"

    def handle_redirect(self) -> str:
        return "token"

    def get_authorization_url(self, state: str) -> str:
        return "https://example.com/authorize"


def test_access_allowed_by_default():
    handler = _DummyHandler()
    assert handler.access_allowed(request=None) is True


def test_access_allowed_can_be_overridden():
    class _DeniedHandler(_DummyHandler):
        def access_allowed(self, request) -> bool:  # type: ignore[no-untyped-def]
            return False

    handler = _DeniedHandler()
    assert handler.access_allowed(request=None) is False
