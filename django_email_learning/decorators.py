import typing
from functools import wraps

from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse

from django_email_learning.apps import PLATFORM_ADMIN_GROUP_NAME
from django_email_learning.models import ApiKeyType, OrganizationUser
from django_email_learning.services.api_key_service import (
    ApiKeyAuthenticationError,
    authenticate_token,
    extract_bearer_token,
)


def is_platform_admin() -> typing.Callable:
    def decorator(view_func: typing.Callable) -> typing.Callable:
        @wraps(view_func)
        def _wrapped_view(request, *view_args, **view_kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
            if not request.user.is_authenticated:
                return JsonResponse({"error": "Unauthorized"}, status=401)

            if (
                not request.user.is_superuser
                and not request.user.groups.filter(name=PLATFORM_ADMIN_GROUP_NAME).exists()
            ):
                return JsonResponse({"error": "Forbidden"}, status=403)
            return view_func(request, *view_args, **view_kwargs)

        return _wrapped_view

    return decorator


def accessible_for(roles: set[str]) -> typing.Callable:
    def decorator(view_func: typing.Callable) -> typing.Callable:
        @wraps(view_func)
        def _wrapped_view(request, *view_args, **view_kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
            if "organization_id" not in view_kwargs:
                raise ImproperlyConfigured(
                    f"accessible_for decorator requires 'organization_id' in URL kwargs, "
                    f"but it was not found for view '{view_func.__name__}'."
                )

            user = request.user
            if not user.is_authenticated:
                return JsonResponse({"error": "Unauthorized"}, status=401)

            if not user.is_superuser:
                has_access = OrganizationUser.objects.filter(  # type: ignore[misc]
                    user=user,
                    organization_id=view_kwargs["organization_id"],
                    role__in=roles,
                ).exists()
                if not has_access:
                    return JsonResponse({"error": "Forbidden"}, status=403)
            return view_func(request, *view_args, **view_kwargs)

        return _wrapped_view

    return decorator


def _resolve_active_organization_id(
    request: typing.Any,
    view_kwargs: dict,
    resolve_org_id: typing.Optional[typing.Callable] = None,
    allow_active_org_fallback: bool = False,
) -> typing.Optional[int]:
    """Resolve the organization ID that authorization should be checked against.

    Resolution order:
    1. URL kwarg ``organization_id`` (API / detail views) — the caller explicitly
       named the organization it wants to act on.
    2. ``resolve_org_id(request, view_kwargs)``, if provided — looks up the
       organization that *owns* the object referenced elsewhere in the URL
       (e.g. a ``course_id`` that isn't itself scoped by an ``organization_id``
       segment). This is required for any view keyed on an object ID rather
       than an explicit organization ID, otherwise a user could pass the
       membership check for their own org while acting on an object that
       belongs to a different org.
    3. Only if ``allow_active_org_fallback`` is set: the session's
       ``active_organization_id``. This is only safe for views that don't
       address a specific object by ID (e.g. "list learners for my active
       org") — it resolves to "the org the user is currently working in",
       not "the org that owns the requested resource", so it must never be
       used to gate access to a specific object. Deliberately does not fall
       back further to the user's first org membership — an arbitrary
       membership is not the same as the org the user actually intends to
       act on, so if the session hasn't been seeded yet we fail closed
       rather than guess.

    Returns ``None`` if no organization could be resolved. Callers must treat
    that as "deny" rather than skipping the check.
    """
    if "organization_id" in view_kwargs:
        return view_kwargs["organization_id"]
    if resolve_org_id is not None:
        return resolve_org_id(request, view_kwargs)
    if allow_active_org_fallback:
        return request.session.get("active_organization_id")
    return None


def is_an_organization_member(
    only_admin: bool = False,
    resolve_org_id: typing.Optional[typing.Callable] = None,
    allow_active_org_fallback: bool = False,
) -> typing.Callable:
    def decorator(view_func: typing.Callable) -> typing.Callable:
        @wraps(view_func)
        def _wrapped_view(request, *view_args, **view_kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
            user = request.user
            if not user.is_authenticated:
                return JsonResponse({"error": "Unauthorized"}, status=401)

            if not user.is_superuser:
                organization_id = _resolve_active_organization_id(
                    request,
                    view_kwargs,
                    resolve_org_id=resolve_org_id,
                    allow_active_org_fallback=allow_active_org_fallback,
                )
                if organization_id is None:
                    return JsonResponse({"error": "Forbidden"}, status=403)
                qs = OrganizationUser.objects.filter(  # type: ignore[misc]
                    user=user,
                    organization_id=organization_id,
                )
                if only_admin:
                    qs = qs.filter(role="admin")
                if not qs.exists():
                    return JsonResponse({"error": "Forbidden"}, status=403)
            return view_func(request, *view_args, **view_kwargs)

        return _wrapped_view

    return decorator


def check_api_key() -> typing.Callable:
    """Authenticates a *platform* API key.

    The key type is asserted positively rather than inferred from the key
    having no organization: these endpoints act deployment-wide, so an
    organization key must never reach them by default.
    """

    def decorator(view_func: typing.Callable) -> typing.Callable:
        @wraps(view_func)
        def _wrapped_view(request, *view_args, **view_kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
            try:
                api_key = authenticate_token(extract_bearer_token(request))
            except ApiKeyAuthenticationError as e:
                return JsonResponse({"error": e.message}, status=e.status)

            if api_key.key_type != ApiKeyType.PLATFORM:
                return JsonResponse({"error": "Forbidden"}, status=403)

            request.api_key = api_key
            return view_func(request, *view_args, **view_kwargs)

        return _wrapped_view

    return decorator


def require_organization_api_key(scopes: typing.Iterable[str] = ()) -> typing.Callable:
    """Authenticates an *organization* API key carrying all of `scopes`.

    Binds `request.api_key` and `request.organization`. The organization is
    taken from the key itself; a view must read it from there rather than from
    the URL, or a caller could act on an organization its key doesn't cover.
    Where a URL does name an organization it has to agree with the key.
    """
    required_scopes = set(scopes)

    def decorator(view_func: typing.Callable) -> typing.Callable:
        @wraps(view_func)
        def _wrapped_view(request, *view_args, **view_kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
            try:
                api_key = authenticate_token(extract_bearer_token(request))
            except ApiKeyAuthenticationError as e:
                return JsonResponse({"error": e.message}, status=e.status)

            if api_key.key_type != ApiKeyType.ORGANIZATION:
                return JsonResponse({"error": "Forbidden"}, status=403)

            missing_scopes = required_scopes - set(api_key.scopes)
            if missing_scopes:
                return JsonResponse(
                    {"error": f"API key is missing required scope(s): {', '.join(sorted(missing_scopes))}"},
                    status=403,
                )

            # 404 rather than 403 for a mismatch: a key holder shouldn't be able
            # to probe which other organization ids exist.
            if "organization_id" in view_kwargs and view_kwargs["organization_id"] != api_key.organization_id:
                return JsonResponse({"error": "Not found"}, status=404)

            request.api_key = api_key
            request.organization = api_key.organization
            return view_func(request, *view_args, **view_kwargs)

        # Published so the OpenAPI generator can read the scopes off the view
        # rather than being told them a second time. The documented security
        # requirement is then the enforced one by construction, and can't drift.
        _wrapped_view.required_api_key_scopes = frozenset(required_scopes)  # type: ignore[attr-defined]
        return _wrapped_view

    return decorator
