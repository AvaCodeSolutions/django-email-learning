from .serializers import CreateSessionRequest


class OAuthSessionRequestMixin:
    def get_create_session_request_class(self) -> type[CreateSessionRequest]:
        """Hook for library users to plug in their own OAuth session request serializer.

        Override in a subclass to support custom handler types beyond the
        built-in ones. SessionsView and RedirectView must agree on the same
        class for a session's create -> redirect round trip to work, so this
        is shared between both views rather than defined separately on each.
        """
        return CreateSessionRequest
