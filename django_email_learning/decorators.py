from functools import wraps
from django.http import JsonResponse
from django_email_learning.models import OrganizationUser
import typing


def is_platform_admin() -> typing.Callable:
    def decorator(view_func: typing.Callable) -> typing.Callable:
        @wraps(view_func)
        def _wrapped_view(request, *view_args, **view_kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
            if not request.user.is_authenticated:
                return JsonResponse({"error": "Unauthorized"}, status=401)

            if (
                not request.user.is_superuser
                and not request.user.groups.filter(name="Platform Admins").exists()
            ):
                return JsonResponse({"error": "Forbidden"}, status=403)
            return view_func(request, *view_args, **view_kwargs)

        return _wrapped_view

    return decorator


def accessible_for(roles: set[str]) -> typing.Callable:
    def decorator(view_func: typing.Callable) -> typing.Callable:
        @wraps(view_func)
        def _wrapped_view(request, *view_args, **view_kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
            user = request.user
            if not user.is_authenticated:
                return JsonResponse({"error": "Unauthorized"}, status=401)

            if not user.is_superuser:
                has_access = OrganizationUser.objects.filter(  # type: ignore[misc]
                    user=user,
                    organization_id=view_kwargs.get("organization_id"),
                    role__in=roles,
                ).exists()
                if not has_access:
                    return JsonResponse({"error": "Forbidden"}, status=403)
            return view_func(request, *view_args, **view_kwargs)

        return _wrapped_view

    return decorator


def is_an_organization_member() -> typing.Callable:
    def decorator(view_func: typing.Callable) -> typing.Callable:
        @wraps(view_func)
        def _wrapped_view(request, *view_args, **view_kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
            user = request.user
            if not user.is_authenticated:
                return JsonResponse({"error": "Unauthorized"}, status=401)

            if not user.is_superuser:
                has_access = OrganizationUser.objects.filter(  # type: ignore[misc]
                    user=user
                ).exists()
                if not has_access:
                    return JsonResponse({"error": "Forbidden"}, status=403)
            return view_func(request, *view_args, **view_kwargs)

        return _wrapped_view

    return decorator
