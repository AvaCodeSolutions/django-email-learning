from django_email_learning.oauth_integrations.mixins import OAuthSessionRequestMixin
from django_email_learning.oauth_integrations.serializers import CreateSessionRequest


def test_get_create_session_request_class_defaults_to_create_session_request():
    mixin = OAuthSessionRequestMixin()
    assert mixin.get_create_session_request_class() is CreateSessionRequest


def test_get_create_session_request_class_can_be_overridden():
    class _CustomCreateSessionRequest(CreateSessionRequest):
        pass

    class _CustomMixin(OAuthSessionRequestMixin):
        def get_create_session_request_class(self) -> type[CreateSessionRequest]:
            return _CustomCreateSessionRequest

    mixin = _CustomMixin()
    assert mixin.get_create_session_request_class() is _CustomCreateSessionRequest
