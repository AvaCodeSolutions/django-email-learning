import pytest
from django.urls import reverse
from django.utils import timezone

from django_email_learning.models import Newsletter, NewsletterSubscriber


@pytest.fixture()
def newsletter(db):
    return Newsletter.objects.create(title="Weekly Digest", language="en", organization_id=1)


def list_url(organization_id: int, newsletter_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:newsletter_subscribers_list",
        kwargs={"organization_id": organization_id, "newsletter_id": newsletter_id},
    )


def csv_url(organization_id: int, newsletter_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:newsletter_subscribers_csv",
        kwargs={"organization_id": organization_id, "newsletter_id": newsletter_id},
    )


def test_subscriber_list_includes_confirmation_status(superadmin_client, newsletter):
    NewsletterSubscriber.objects.create(
        newsletter=newsletter, email="confirmed@example.com", confirmed_at=timezone.now()
    )
    NewsletterSubscriber.objects.create(newsletter=newsletter, email="pending@example.com")

    response = superadmin_client.get(list_url(1, newsletter.id))

    assert response.status_code == 200
    items = {item["email"]: item for item in response.json()["items"]}
    assert items["confirmed@example.com"]["is_confirmed"] is True
    assert items["pending@example.com"]["is_confirmed"] is False


def test_subscribers_csv_includes_confirmed_column(superadmin_client, newsletter):
    NewsletterSubscriber.objects.create(
        newsletter=newsletter, email="confirmed@example.com", confirmed_at=timezone.now()
    )
    NewsletterSubscriber.objects.create(newsletter=newsletter, email="pending@example.com")

    response = superadmin_client.get(csv_url(1, newsletter.id))

    assert response.status_code == 200
    content = response.content.decode()
    assert content.splitlines()[0] == "id,email,subscribed_at,confirmed"
    rows = {line.split(",")[1]: line for line in content.splitlines()[1:]}
    assert rows["confirmed@example.com"].endswith(",True")
    assert rows["pending@example.com"].endswith(",False")
