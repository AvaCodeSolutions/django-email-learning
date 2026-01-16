from django.http import JsonResponse
from django.db.models import QuerySet
from typing import Any


class PaginatedApiMixin:
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        page = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("page_size", 50))
        offset = (page - 1) * page_size

        qs = self.get_query_set(request=request)

        items = qs[offset : offset + page_size]
        item_serializer_class = self.get_item_serializer_class()
        count = qs.count()

        response_list = []
        for item in items:
            response_list.append(
                item_serializer_class.model_validate(item).model_dump()
            )
        return JsonResponse(
            {
                "items": response_list,
                "count": count,
                "page": page,
                "page_size": page_size,
                "has_more": count > offset + page_size,
            },
            status=200,
        )

    def get_query_set(self, request: Any) -> QuerySet:
        raise NotImplementedError("Subclasses must implement get_query_set method")

    def get_item_serializer_class(self) -> Any:
        raise NotImplementedError(
            "Subclasses must implement get_item_serializer_class method"
        )
