import json

import pytest
from django_email_learning.ai.language_models import LanguageModel


INPUT_TEXT = "Draft text which is long enough to pass validation"


def get_url(organization_id: int) -> str:
    return f"/email_learning/api/ai/organizations/{organization_id}/edit-text/"


def test_edit_text_calls_model_adapter(editor_client, monkeypatch):
    calls: dict[str, str] = {}

    class DummyAdapter:
        def edit_text(self, text: str, model: str) -> str:
            calls["text"] = text
            calls["model"] = model
            return "Edited text"

    monkeypatch.setattr(LanguageModel.GPT_5_NANO, "adapter_class", DummyAdapter)

    response = editor_client.post(
        get_url(1),
        data=json.dumps({"input": INPUT_TEXT}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {"edited_text": "Edited text"}
    assert calls == {
        "text": INPUT_TEXT,
        "model": LanguageModel.GPT_5_NANO.model_name,
    }


def test_edit_text_accepts_markup_in_input(editor_client, monkeypatch):
    calls: dict[str, str] = {}

    class DummyAdapter:
        def edit_text(self, text: str, model: str) -> str:
            calls["text"] = text
            calls["model"] = model
            return "Edited markup text"

    monkeypatch.setattr(LanguageModel.GPT_5_NANO, "adapter_class", DummyAdapter)

    payload = {
        "input": "Draft <strong>text</strong> which is long enough to pass validation",
    }
    response = editor_client.post(
        get_url(1),
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {"edited_text": "Edited markup text"}
    assert calls == {
        "text": payload["input"],
        "model": LanguageModel.GPT_5_NANO.model_name,
    }


@pytest.mark.parametrize(
    "client", ["editor", "platform_admin", "org_admin"], indirect=["client"]
)
def test_edit_text_accessible_for_editor_and_admin(client, monkeypatch):
    class DummyAdapter:
        def edit_text(self, text: str, model: str) -> str:
            return "Edited text"

    monkeypatch.setattr(LanguageModel.GPT_5_NANO, "adapter_class", DummyAdapter)

    response = client.post(
        get_url(1),
        data=json.dumps({"input": INPUT_TEXT}),
        content_type="application/json",
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "client,expected_status",
    [("viewer", 403), ("anonymous", 401)],
    indirect=["client"],
)
def test_edit_text_not_accessible_for_viewer_or_anonymous(client, expected_status):
    response = client.post(
        get_url(1),
        data=json.dumps({"input": INPUT_TEXT}),
        content_type="application/json",
    )

    assert response.status_code == expected_status


@pytest.mark.parametrize("length", [39, 501])
def test_edit_text_validation_error(editor_client, length):
    response = editor_client.post(
        get_url(1),
        data=json.dumps({"input": "x" * length}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "error" in response.json()
