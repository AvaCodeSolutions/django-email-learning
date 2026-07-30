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
    assert response["Cache-Control"] == "public, max-age=3600"
    content = response.content.decode()
    assert "customElements.define('del-enroll-form'" in content
    assert "class DelEnrollForm extends HTMLElement" in content
    assert ":host { display:block; width:350px; max-width:100%;" in content
    assert "customElements.define('del-newsletter-form'" in content
    assert "class DelNewsletterForm extends HTMLElement" in content


def test_embed_script_builds_dom_without_innerhtml(anonymous_client, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}

    response = anonymous_client.get(URL)

    content = response.content.decode()
    # User-controlled values must be attached as data (createElement /
    # textContent / setAttribute), never spliced into an innerHTML string, so
    # attacker-controlled attributes cannot break out into markup/handlers.
    assert "shadow.innerHTML" not in content
    assert "document.createElement" in content
    # Sanitizers for the values that land in attributes.
    assert "function safeImageUrl(" in content
    assert "function safeCssColor(" in content
    assert "url.protocol === 'http:' || url.protocol === 'https:'" in content


def test_embed_script_sanitizes_image_and_color_attributes(anonymous_client, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}

    response = anonymous_client.get(URL)

    content = response.content.decode()
    # The image src and both colors run through the sanitizers before use.
    assert "safeImageUrl(this.getAttribute('course_image') || '')" in content
    assert "safeCssColor(this.getAttribute('button_bg_color') || '', '#4f46e5')" in content
    assert "safeCssColor(this.getAttribute('button_text_color') || '', '#ffffff')" in content
    # del-newsletter-form's colors run through the same sanitizer.
    assert content.count("safeCssColor(this.getAttribute('button_bg_color') || '', '#4f46e5')") == 2
    assert content.count("safeCssColor(this.getAttribute('button_text_color') || '', '#ffffff')") == 2


def test_embed_script_image_sanitizer_rejects_blank_values(anonymous_client, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}

    response = anonymous_client.get(URL)

    content = response.content.decode()
    # new URL('', base) resolves to the host page's own URL instead of throwing,
    # so a blank course_image (the "show course image" switch turned off, or a
    # course with no image) would otherwise render an <img> pointing at the
    # embedding page. The behavioural cover for this lives in
    # frontend/src/test/public/embedScript.test.js.
    assert "if (!value.trim()) {" in content


def test_embed_script_newsletter_form_posts_to_subscribe_endpoint(anonymous_client, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}

    response = anonymous_client.get(URL)

    content = response.content.decode()
    assert "fetch(API_BASE + token + '/newsletters/subscribe/'" in content
    assert "newsletter_ids: [Number(newsletterId)]" in content


def test_embed_script_contains_deployment_api_base(anonymous_client, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}

    response = anonymous_client.get(URL)

    content = response.content.decode()
    assert embed_api_base_url() in content
    # No leftover placeholder from the reverse()-with-placeholder trick.
    assert "TOKEN_PLACEHOLDER" not in content


def test_embed_script_supports_preview_mode(anonymous_client, settings):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "EMBEDDABLE_ENROLLMENT_ENABLED": True}

    response = anonymous_client.get(URL)

    content = response.content.decode()
    assert "var isPreview = this.hasAttribute('preview');" in content
    assert "emailInput.readOnly = true;" in content
    assert "submitButton.disabled = isPreview;" in content
    assert "if (isPreview) {" in content


def test_embed_api_base_url_shape(settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "SITE_BASE_URL": "https://example.com",
    }
    assert embed_api_base_url() == "https://example.com/email_learning/api/public/embed/"
