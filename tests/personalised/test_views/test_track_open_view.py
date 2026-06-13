from django.urls import reverse


URL_NAME = "django_email_learning:personalised:track_open"


def _url(hash_value: str) -> str:
    return reverse(URL_NAME, kwargs={"hash_value": hash_value})


def test_returns_transparent_gif(content_delivery, anonymous_client):
    response = anonymous_client.get(_url(content_delivery.hash_value))

    assert response.status_code == 200
    assert response["Content-Type"] == "image/gif"
    # GIF89a magic bytes
    assert response.content[:6] == b"GIF89a"


def test_sets_opened_at_on_first_request(content_delivery, anonymous_client):
    assert content_delivery.opened_at is None

    anonymous_client.get(_url(content_delivery.hash_value))

    content_delivery.refresh_from_db()
    assert content_delivery.opened_at is not None


def test_does_not_overwrite_opened_at_on_subsequent_requests(
    content_delivery, anonymous_client
):
    anonymous_client.get(_url(content_delivery.hash_value))
    content_delivery.refresh_from_db()
    first_opened_at = content_delivery.opened_at

    anonymous_client.get(_url(content_delivery.hash_value))
    content_delivery.refresh_from_db()

    assert content_delivery.opened_at == first_opened_at


def test_invalid_hash_still_returns_gif(anonymous_client, db):
    response = anonymous_client.get(_url("invalidhash"))

    assert response.status_code == 200
    assert response["Content-Type"] == "image/gif"
    assert response.content[:6] == b"GIF89a"


def test_invalid_hash_does_not_raise(anonymous_client, db):
    # Should never 404 or 500 — email clients must always receive the pixel
    response = anonymous_client.get(_url("doesnotexist"))
    assert response.status_code == 200
