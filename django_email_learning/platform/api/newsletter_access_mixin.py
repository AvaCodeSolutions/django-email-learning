from django.http import HttpRequest, JsonResponse


class NewsletterAccessMixin:
    def newsletter_access_allowed(self, request: HttpRequest, *args, **kwargs) -> bool:  # type: ignore[no-untyped-def]
        """Hook for library users to gate access to the newsletter API.

        Override in a subclass to implement custom access logic (e.g. feature
        flags, subscription plans). Runs before the standard role-based
        access checks.
        """
        return True

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        if not self.newsletter_access_allowed(request, *args, **kwargs):
            return JsonResponse({"error": "Forbidden"}, status=403)
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]
