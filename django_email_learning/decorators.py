from functools import wraps
from django.http import JsonResponse
from django_email_learning.models import OrganizationUser
from django_email_learning.apps import PLATFORM_ADMIN_GROUP_NAME
from django_email_learning.services.jwt_service import decode_jwt, InvalidTokenException
from django_email_learning.models import ApiKey
import typing


def is_platform_admin() -> typing.Callable:
    def decorator(view_func: typing.Callable) -> typing.Callable:
        @wraps(view_func)
        def _wrapped_view(request, *view_args, **view_kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
            if not request.user.is_authenticated:
                return JsonResponse({"error": "Unauthorized"}, status=401)

            if (
                not request.user.is_superuser
                and not request.user.groups.filter(
                    name=PLATFORM_ADMIN_GROUP_NAME
                ).exists()
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


def check_api_key() -> typing.Callable:
    def decorator(view_func: typing.Callable) -> typing.Callable:
        @wraps(view_func)
        def _wrapped_view(request, *view_args, **view_kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
            authorization_header = request.headers.get("Authorization")
            if not authorization_header:
                return JsonResponse(
                    {"error": "Authorization header missing"}, status=401
                )
            authorization_header_parts = authorization_header.split(" ")
            if (
                len(authorization_header_parts) != 2
                or authorization_header_parts[0] != "Bearer"
            ):
                return JsonResponse(
                    {
                        "error": "Invalid Authorization header format. Expected: Bearer <API_KEY>"
                    },
                    status=401,
                )
            api_key = authorization_header_parts[1]
            try:
                key_data = decode_jwt(api_key)
                possible_keys = ApiKey.objects.filter(salt=key_data["salt"])
                key_matched = False
                for possible_key in possible_keys:
                    key_value = possible_key.decrypt_password(possible_key.key)
                    if key_value == key_data["key"]:
                        key_matched = True
                        break
                if not key_matched:
                    return JsonResponse({"error": "Invalid API key"}, status=401)
            except InvalidTokenException:
                return JsonResponse({"error": "Invalid Json Web Token"}, status=401)
            except KeyError:
                return JsonResponse(
                    {"error": "Json Web Token missing required fields"}, status=401
                )

            try:
                api_key = ApiKey.objects.get(salt=key_data["salt"])
            except ApiKey.DoesNotExist:
                return JsonResponse({"error": "Invalid API key"}, status=401)

            return view_func(request, *view_args, **view_kwargs)

        return _wrapped_view

    return decorator
