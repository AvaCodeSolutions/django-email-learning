import pytest
from django.urls import reverse

from django_email_learning.models import Newsletter


@pytest.fixture()
def newsletter(db):
    return Newsletter.objects.create(title="Weekly Digest", language="en", organization_id=1)


def get_url(newsletter, organization_id: int = 1) -> str:
    return reverse(
        "django_email_learning:platform:newsletter_detail_view",
        kwargs={"organization_id": organization_id, "newsletter_id": newsletter.id},
    )


def test_newsletter_detail_view_redirects_anonymous(anonymous_client, newsletter):
    response = anonymous_client.get(get_url(newsletter))
    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


def test_sendout_blocked_default_message_uses_builtin_default(superadmin_client, newsletter):
    response = superadmin_client.get(get_url(newsletter))
    assert response.status_code == 200
    assert (
        response.context["appContext"]["localeMessages"]["sendout_blocked_default_message"]
        == "This sendout was blocked."
    )


def test_sendout_blocked_default_message_can_be_overridden_via_settings(superadmin_client, newsletter, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "NEWSLETTERS": {"SENDOUT_BLOCKED_MESSAGE": "Custom limit reached message."},
    }

    response = superadmin_client.get(get_url(newsletter))

    assert response.status_code == 200
    assert (
        response.context["appContext"]["localeMessages"]["sendout_blocked_default_message"]
        == "Custom limit reached message."
    )
