from django.urls import reverse

from django_email_learning.public.embed_script import embed_api_base_url

URL = reverse("django_email_learning:public:embed_script")


def test_embed_script_disabled_by_default(anonymous_client, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": False}
    response = anonymous_client.get(URL)
    assert response.status_code == 404


def test_embed_script_served_when_enabled(anonymous_client, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}

    response = anonymous_client.get(URL)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/javascript"
    assert response["Cache-Control"] == "no-cache"
    content = response.content.decode()
    assert "customElements.define('del-enroll-form'" in content
    assert "class DelEnrollForm extends HTMLElement" in content
    assert ":host { display:block; width:350px; max-width:100%; }" in content


def test_embed_script_contains_deployment_api_base(anonymous_client, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}

    response = anonymous_client.get(URL)

    content = response.content.decode()
    assert embed_api_base_url() in content
    # No leftover placeholder from the reverse()-with-placeholder trick.
    assert "TOKEN_PLACEHOLDER" not in content


def test_embed_api_base_url_shape(settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "SITE_BASE_URL": "https://example.com",
    }
    assert embed_api_base_url() == "https://example.com/email_learning/api/public/embed/"
