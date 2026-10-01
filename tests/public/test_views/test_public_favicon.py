from io import BytesIO

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.urls import reverse
from PIL import Image

from django_email_learning.models import Organization
from django_email_learning.public.views import get_favicon_links


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def lockups(settings):
    def set_lockups(light=None, dark=None):
        settings.DJANGO_EMAIL_LEARNING = {
            **settings.DJANGO_EMAIL_LEARNING,
            "LOGO": {"VERTICAL_LOCKUP": {"LIGHT_BACKGROUND": light, "DARK_BACKGROUND": dark}},
        }

    return set_lockups


def png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (120, 60), "red").save(buffer, format="PNG")
    return buffer.getvalue()


def test_favicon_links_prefer_the_rendered_favicon(db, lockups):
    lockups(light="/static/v-light.png")
    organization = Organization.objects.get(id=1)
    organization.logo = default_storage.save("organization_logos/1/logo.png", ContentFile(png_bytes()))
    organization.save()

    assert get_favicon_links(organization) == [{"href": f"/media/{organization.favicon.name}", "type": "image/png"}]


def test_favicon_links_use_a_logo_without_a_rendered_favicon(db, lockups):
    lockups(light="/static/v-light.png")
    organization = Organization.objects.get(id=1)
    organization.logo = default_storage.save("organization_logos/1/logo.svg", ContentFile(b"<svg/>"))
    organization.save()

    assert get_favicon_links(organization) == [{"href": "/media/organization_logos/1/logo.svg"}]


def test_favicon_links_offer_both_lockups_by_colour_scheme(db, lockups):
    lockups(light="/static/v-light.png", dark="/static/v-dark.png")

    assert get_favicon_links(Organization.objects.get(id=1)) == [
        {"href": "/static/v-light.png", "media": "(prefers-color-scheme: light)"},
        {"href": "/static/v-dark.png", "media": "(prefers-color-scheme: dark)"},
    ]


@pytest.mark.parametrize("light, dark", [("/static/v-light.png", None), (None, "/static/v-dark.png")])
def test_favicon_links_use_the_only_lockup_set(db, lockups, light, dark):
    lockups(light=light, dark=dark)

    assert get_favicon_links(Organization.objects.get(id=1)) == [{"href": light or dark}]


def test_favicon_links_empty_without_logo_or_lockup(db, lockups):
    lockups()

    assert get_favicon_links(Organization.objects.get(id=1)) == []


def test_organization_page_renders_the_organization_favicon(db, anonymous_client):
    organization = Organization.objects.get(id=1)
    organization.logo = default_storage.save("organization_logos/1/logo.png", ContentFile(png_bytes()))
    organization.save()

    url = reverse("django_email_learning:public:organization_view", kwargs={"organization_id": 1})
    html = anonymous_client.get(url).content.decode()

    assert f'<link rel="icon" href="/media/{organization.favicon.name}" type="image/png" />' in html
    assert "static/logo.png" not in html


def test_course_page_renders_the_lockup_favicons(db, anonymous_client, course, lockups):
    lockups(light="/static/v-light.png", dark="/static/v-dark.png")
    course.enabled = True
    course.save()

    url = reverse(
        "django_email_learning:public:course_view",
        kwargs={"organization_id": 1, "course_slug": course.slug},
    )
    html = anonymous_client.get(url).content.decode()

    assert '<link rel="icon" href="/static/v-light.png" media="(prefers-color-scheme: light)" />' in html
    assert '<link rel="icon" href="/static/v-dark.png" media="(prefers-color-scheme: dark)" />' in html


def test_organization_page_falls_back_to_the_library_favicon(db, anonymous_client, lockups):
    lockups()

    url = reverse("django_email_learning:public:organization_view", kwargs={"organization_id": 1})
    html = anonymous_client.get(url).content.decode()

    assert 'type="image/png" href="/static/logo.png"' in html
