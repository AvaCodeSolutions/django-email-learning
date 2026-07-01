import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from pydantic import ValidationError

from django_email_learning.decorators import accessible_for

from .serializers import EditTextRequest


@method_decorator(accessible_for(roles={"admin", "editor", "instructor"}), name="post")
class EditTextView(View):
    def ai_edit_text_access_allowed(self, request, *args, **kwargs) -> bool:  # type: ignore[no-untyped-def]
        """Hook for library users to gate access to the AI text-editing feature.

        Override in a subclass to implement custom access logic (e.g. feature
        flags, subscription plans). Runs before the standard role-based
        access checks.
        """
        return True

    def dispatch(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        if not self.ai_edit_text_access_allowed(request, *args, **kwargs):
            return JsonResponse({"error": "Forbidden"}, status=403)
        return super().dispatch(request, *args, **kwargs)  # type: ignore[return-value]

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = EditTextRequest.model_validate(payload)
            input = serializer.input
            model = serializer.model
            ai_adapter = model.adapter_class()
            edited_text = ai_adapter.edit_text(input, model.model_name)
            return JsonResponse({"edited_text": edited_text})
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)
