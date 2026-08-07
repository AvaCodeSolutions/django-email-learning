import json

import pytest
from django.test import override_settings
from django.urls import reverse

from django_email_learning.organization_api import serializers
from django_email_learning.organization_api.openapi import (
    SCHEMA_REF_TEMPLATE,
    SECURITY_SCHEME_NAME,
    _routed_operations,
    build_openapi_schema,
)

URL = reverse("django_email_learning:api_v1:openapi_schema")


def _refs(node) -> set:
    """Every $ref string anywhere in the document."""
    if isinstance(node, dict):
        found = {node["$ref"]} if "$ref" in node else set()
        return found.union(*(_refs(value) for value in node.values())) if node else found
    if isinstance(node, list):
        return set().union(*(_refs(item) for item in node)) if node else set()
    return set()


def test_schema_endpoint_serves_the_document(api_client, db):
    response = api_client.get(URL)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"

    schema = json.loads(response.content)
    assert schema["openapi"].startswith("3.1")
    assert schema["info"]["title"]
    assert schema["paths"]


def test_schema_endpoint_needs_no_api_key(api_client, db):
    """The document describes the API's shape and contains no organization
    data, so it isn't gated behind a credential."""
    assert "HTTP_AUTHORIZATION" not in api_client.defaults
    assert api_client.get(URL).status_code == 200


@override_settings(DJANGO_EMAIL_LEARNING={"ORGANIZATION_API_DOCS_ENABLED": False})
def test_schema_endpoint_can_be_disabled(api_client, db):
    assert api_client.get(URL).status_code == 404


def test_every_routed_endpoint_is_documented():
    """The drift guard. Adding a v1 endpoint without an OperationSpec fails
    here rather than silently shipping an incomplete document.
    """
    undocumented = [f"{method.upper()} {path}" for _, path, method, _, spec in _routed_operations() if spec is None]
    assert undocumented == [], f"v1 endpoints missing an OperationSpec: {undocumented}"


def test_drift_guard_detects_an_undocumented_endpoint(monkeypatch):
    """Proves the guard above can actually fail. Without this, a bug that made
    `_routed_operations` yield nothing would leave it passing vacuously."""
    from django_email_learning.organization_api.views import EnrollmentsView

    monkeypatch.setattr(EnrollmentsView, "openapi_operations", {}, raising=False)
    assert [method for _, _, method, _, spec in _routed_operations() if spec is None] == ["post"]


def test_documented_scopes_are_the_enforced_scopes():
    """Security requirements are read off the auth decorator, not restated in
    the spec, so the document can't claim a scope the code doesn't check."""
    schema = build_openapi_schema()

    checked = 0
    for _, path, method, handler, spec in _routed_operations():
        if spec is None:
            continue
        enforced = getattr(handler, "required_api_key_scopes", None)
        if enforced is None:
            continue
        documented = schema["paths"][path][method]["security"][0][SECURITY_SCHEME_NAME]
        assert documented == sorted(str(scope) for scope in enforced)
        checked += 1

    assert checked > 0, "no scoped operations were checked - the guarantee is untested"


def test_path_matches_real_routing():
    """Paths come from the URLconf, so they follow wherever the including
    project mounts the API rather than assuming /api/v1/."""
    schema = build_openapi_schema()
    assert reverse("django_email_learning:api_v1:enrollments") in schema["paths"]


def test_request_schema_comes_from_the_pydantic_model():
    schema = build_openapi_schema()
    operation = schema["paths"][reverse("django_email_learning:api_v1:enrollments")]["post"]

    ref = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    assert ref == SCHEMA_REF_TEMPLATE.format(model="EnrollmentCreateRequest")

    documented = schema["components"]["schemas"]["EnrollmentCreateRequest"]
    assert set(documented["properties"]) == set(serializers.EnrollmentCreateRequest.model_json_schema()["properties"])


def test_nested_models_are_lifted_into_components():
    """EnrollmentCreatedResponse nests EnrollmentResponse; Pydantic emits that
    into $defs, which has to be hoisted or the refs dangle."""
    schema = build_openapi_schema()
    assert "EnrollmentResponse" in schema["components"]["schemas"]
    assert "$defs" not in schema["components"]["schemas"]["EnrollmentCreatedResponse"]


def test_no_dangling_references():
    schema = build_openapi_schema()
    defined = {SCHEMA_REF_TEMPLATE.format(model=name) for name in schema["components"]["schemas"]}
    assert _refs(schema["paths"]) <= defined
    assert _refs(schema["components"]["schemas"]) <= defined


def test_every_documented_response_has_a_description():
    """OpenAPI requires it, and an empty one renders as a blank row in every
    tool that consumes this."""
    schema = build_openapi_schema()
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            for status, response in operation["responses"].items():
                assert response["description"].strip(), f"{method.upper()} {path} -> {status}"


def test_operation_ids_are_unique_and_path_independent():
    """operationId names the generated client method, so it must not embed the
    deployment's mount prefix."""
    schema = build_openapi_schema()
    operation_ids = [operation["operationId"] for methods in schema["paths"].values() for operation in methods.values()]
    assert len(operation_ids) == len(set(operation_ids))
    assert all("/" not in operation_id for operation_id in operation_ids)


@pytest.mark.parametrize("scheme_field", ["type", "scheme"])
def test_security_scheme_is_declared(scheme_field):
    schema = build_openapi_schema()
    assert schema["components"]["securitySchemes"][SECURITY_SCHEME_NAME][scheme_field]
