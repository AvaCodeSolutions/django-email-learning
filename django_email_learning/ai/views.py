from django.utils.decorators import method_decorator
from django_email_learning.decorators import accessible_for
from django.http import JsonResponse
from django.views import View
from pydantic import ValidationError
from .serializers import EditTextRequest
import json


@method_decorator(accessible_for(roles={"admin", "editor"}), name="post")
class EditTextView(View):
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
