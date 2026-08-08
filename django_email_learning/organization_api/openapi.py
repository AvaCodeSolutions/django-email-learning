"""Builds an OpenAPI 3.1 document for the v1 API from the code that serves it.

Three things are read rather than restated, so the document can't drift from
the implementation:

* **Paths** come from the URLconf that is actually routed.
* **Schemas** come from the Pydantic models the views validate and serialise
  with. Pydantic v2 emits JSON Schema 2020-12, which is what OpenAPI 3.1 uses,
  so no translation is needed.
* **Security** comes from the scopes the auth decorator enforces, which it
  publishes as ``required_api_key_scopes``.

What is declared by hand is the operation prose and the status-code map, in an
``openapi_operations`` attribute on each view. `test_openapi.py` fails if a
routed endpoint has no entry, so adding one without documenting it breaks the
build rather than silently shipping an incomplete document.
"""

import re
import typing

from django.conf import settings
from django.urls import reverse
from pydantic import BaseModel

OPENAPI_VERSION = "3.1.0"
API_VERSION = "1.0.0"
SECURITY_SCHEME_NAME = "organizationApiKey"
SCHEMA_REF_TEMPLATE = "#/components/schemas/{model}"

# Django path converters, mapped to the OpenAPI types they accept.
_CONVERTER_TYPES = {
    "int": {"type": "integer"},
    "str": {"type": "string"},
    "slug": {"type": "string"},
    "uuid": {"type": "string", "format": "uuid"},
    "path": {"type": "string"},
}
_PATH_PARAM_RE = re.compile(r"<(?:(?P<converter>[^:>]+):)?(?P<name>[^>]+)>")


class ResponseSpec(typing.NamedTuple):
    """One documented status code. `model` is None for a body-less response."""

    description: str
    model: type[BaseModel] | None = None


class OperationSpec(typing.NamedTuple):
    """The prose and status-code map for one operation.

    Deliberately does not carry the path, the method or the required scopes:
    those are read from the routing and the decorator, and duplicating them
    here would create exactly the drift this module exists to avoid.

    `operation_id` names the generated client method, so it is set explicitly
    rather than derived from the path — the mount prefix is the including
    project's choice, and generated clients shouldn't rename themselves
    because a deployment moved the API.
    """

    operation_id: str
    summary: str
    description: str = ""
    request: type[BaseModel] | None = None
    responses: dict[int, ResponseSpec] = {}


def _openapi_path(route: str, prefix: str) -> str:
    """Converts a Django route to an OpenAPI path template."""
    return prefix + _PATH_PARAM_RE.sub(lambda m: "{" + m.group("name") + "}", route)


def _path_parameters(route: str) -> list[dict]:
    return [
        {
            "name": match.group("name"),
            "in": "path",
            "required": True,
            "schema": _CONVERTER_TYPES.get(match.group("converter") or "str", {"type": "string"}),
        }
        for match in _PATH_PARAM_RE.finditer(route)
    ]


def _urlpatterns() -> list:
    """Imported at call time, not module scope: the views this documents import
    `OperationSpec` from here, and the URLconf imports those views."""
    from django_email_learning.organization_api import urls as organization_api_urls

    return organization_api_urls.urlpatterns


def _mount_prefix() -> str:
    """Where the v1 URLconf is actually mounted.

    Derived by reversing a real route and removing its own segment, rather than
    hardcoding ``/api/v1/`` — the including project chooses the prefix, and a
    library can't assume it.
    """
    pattern = _urlpatterns()[0]
    full_path = reverse(f"django_email_learning:api_v1:{pattern.name}")
    route = str(pattern.pattern)
    return full_path[: len(full_path) - len(route)]


def _model_schema(model: type[BaseModel], components: dict) -> dict:
    """Returns a ``$ref`` to `model`, registering it and its dependencies.

    Pydantic emits nested models into ``$defs``; those are lifted into the
    shared components section so that models referenced from more than one
    operation are defined once.
    """
    schema = model.model_json_schema(ref_template=SCHEMA_REF_TEMPLATE)
    components.update(schema.pop("$defs", {}))
    components[model.__name__] = schema
    return {"$ref": SCHEMA_REF_TEMPLATE.format(model=model.__name__)}


def _routed_operations() -> typing.Iterator[tuple[str, str, str, typing.Callable, OperationSpec | None]]:
    """Yields (route, openapi_path, http_method, handler, spec) for every
    routed v1 endpoint, including any the view has not documented."""
    prefix = _mount_prefix()
    for pattern in _urlpatterns():
        view_class = getattr(pattern.callback, "view_class", None)
        if view_class is None or getattr(view_class, "openapi_exclude", False):
            continue
        route = str(pattern.pattern)
        specs = getattr(view_class, "openapi_operations", {})
        for method in view_class.http_method_names:
            handler = getattr(view_class, method, None)
            if handler is None or method == "options":
                continue
            yield route, _openapi_path(route, prefix), method, handler, specs.get(method)


def build_openapi_schema() -> dict:
    components: dict = {}
    paths: dict = {}

    DJANGO_EMAIL_LEARNING_CONFIG = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
    OPENAPI_CONFIG = DJANGO_EMAIL_LEARNING_CONFIG.get("OPENAPI", {})
    OPENAPI_TITLE = OPENAPI_CONFIG.get("TITLE", "Django Email Learning — Organization API")

    for route, path, method, handler, spec in _routed_operations():
        if spec is None:
            continue

        operation: dict = {"summary": spec.summary, "operationId": spec.operation_id}
        if spec.description:
            operation["description"] = spec.description

        parameters = _path_parameters(route)
        if parameters:
            operation["parameters"] = parameters

        # Read off the decorator rather than the spec, so the documented
        # requirement is the enforced one.
        scopes = getattr(handler, "required_api_key_scopes", None)
        if scopes is not None:
            operation["security"] = [{SECURITY_SCHEME_NAME: sorted(str(scope) for scope in scopes)}]

        if spec.request is not None:
            operation["requestBody"] = {
                "required": True,
                "content": {"application/json": {"schema": _model_schema(spec.request, components)}},
            }

        operation["responses"] = {
            str(status): (
                {
                    "description": response.description,
                    "content": {"application/json": {"schema": _model_schema(response.model, components)}},
                }
                if response.model is not None
                else {"description": response.description}
            )
            for status, response in sorted(spec.responses.items())
        }

        paths.setdefault(path, {})[method] = operation

    return {
        "openapi": OPENAPI_VERSION,
        "info": {
            "title": OPENAPI_TITLE,
            "version": API_VERSION,
            "description": (
                "Organization-scoped API authenticated with an organization API key. "
                "Every request acts on the organization its key was issued for."
            ),
        },
        "paths": paths,
        "components": {
            "schemas": components,
            "securitySchemes": {
                SECURITY_SCHEME_NAME: {
                    "type": "http",
                    "scheme": "bearer",
                    "description": (
                        "An organization API key, sent as `Authorization: Bearer elk_<key_id>_<secret>`. "
                        "The listed scopes must all be present on the key."
                    ),
                }
            },
        },
    }
