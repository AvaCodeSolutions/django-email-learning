import re
from io import BytesIO

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from PIL import Image

from django_email_learning.models import Organization
from django_email_learning.services.favicon_service import FAVICON_SIZE, make_favicon_png


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def save_logo(name: str, size: tuple[int, int] = (300, 100), color: str = "red") -> str:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return default_storage.save(name, ContentFile(buffer.getvalue()))


def open_favicon(organization: Organization) -> Image.Image:
    with default_storage.open(organization.favicon.name) as favicon_file:
        image = Image.open(favicon_file)
        image.load()
    return image


def test_make_favicon_png_is_square_and_keeps_aspect_ratio():
    buffer = BytesIO()
    Image.new("RGB", (300, 100), "red").save(buffer, format="PNG")
    buffer.seek(0)

    image = Image.open(BytesIO(make_favicon_png(buffer)))

    assert image.size == (FAVICON_SIZE, FAVICON_SIZE)
    assert image.mode == "RGBA"
    # A 3:1 logo fills the width; the bands above and below stay transparent.
    assert image.getpixel((FAVICON_SIZE // 2, FAVICON_SIZE // 2))[3] == 255
    assert image.getpixel((FAVICON_SIZE // 2, 0))[3] == 0


def test_make_favicon_png_trims_transparent_margins():
    logo = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    logo.paste((0, 0, 255, 255), (150, 150, 250, 250))
    buffer = BytesIO()
    logo.save(buffer, format="PNG")
    buffer.seek(0)

    image = Image.open(BytesIO(make_favicon_png(buffer)))

    # The 100px mark alone is scaled to fill the square, not the whole 400px canvas.
    assert image.getpixel((1, 1))[3] == 255


def test_saving_a_logo_renders_a_favicon(db):
    organization = Organization.objects.get(id=1)
    organization.logo = save_logo("organization_logos/1/logo.png")
    organization.save()

    organization.refresh_from_db()
    assert re.fullmatch(r"organization_logos/1/favicon-[0-9a-f]{12}\.png", organization.favicon.name)
    assert open_favicon(organization).size == (FAVICON_SIZE, FAVICON_SIZE)


def test_new_organization_with_logo_renders_a_favicon(db):
    organization = Organization(name="New Org", logo=save_logo("organization_logos/new.png"))
    organization.save()

    organization.refresh_from_db()
    assert organization.favicon.name.startswith(f"organization_logos/{organization.pk}/favicon-")


def test_replacing_the_logo_re_renders_the_favicon(db):
    organization = Organization.objects.get(id=1)
    organization.logo = save_logo("organization_logos/1/red.png", color="red")
    organization.save()
    red_favicon_name = organization.favicon.name
    organization.logo = save_logo("organization_logos/1/blue.png", color="blue")
    organization.save()

    organization.refresh_from_db()
    # A new image gets a new name, so a long-cached old favicon is never served for it.
    assert organization.favicon.name != red_favicon_name
    assert not default_storage.exists(red_favicon_name)
    assert open_favicon(organization).getpixel((FAVICON_SIZE // 2, FAVICON_SIZE // 2)) == (0, 0, 255, 255)


def test_saving_without_changing_the_logo_leaves_the_favicon_alone(db, monkeypatch):
    organization = Organization.objects.get(id=1)
    organization.logo = save_logo("organization_logos/1/logo.png")
    organization.save()

    reloaded = Organization.objects.get(id=1)
    monkeypatch.setattr(Organization, "refresh_favicon", lambda self: pytest.fail("favicon re-rendered"))
    reloaded.name = "Renamed"
    reloaded.save()
    Organization.objects.only("id", "name").get(id=1).save()


def test_removing_the_logo_removes_the_favicon(db):
    organization = Organization.objects.get(id=1)
    organization.logo = save_logo("organization_logos/1/logo.png")
    organization.save()
    favicon_name = organization.favicon.name

    organization.logo = None
    organization.save()

    organization.refresh_from_db()
    assert not organization.favicon
    assert not default_storage.exists(favicon_name)


def test_vector_logo_gets_no_favicon(db):
    organization = Organization.objects.get(id=1)
    organization.logo = default_storage.save("organization_logos/1/logo.svg", ContentFile(b"<svg/>"))
    organization.save()

    organization.refresh_from_db()
    assert not organization.favicon


def test_unreadable_logo_saves_without_a_favicon(db):
    organization = Organization.objects.get(id=1)
    organization.logo = default_storage.save("organization_logos/1/logo.png", ContentFile(b"not an image"))
    organization.save()

    organization.refresh_from_db()
    assert organization.logo.name == "organization_logos/1/logo.png"
    assert not organization.favicon


def test_generate_organization_favicons_renders_missing_favicons(db):
    logo_name = save_logo("organization_logos/1/logo.png")
    # A logo set without save(), as it was for organizations from before favicons.
    Organization.objects.filter(id=1).update(logo=logo_name)

    call_command("generate_organization_favicons")

    assert Organization.objects.get(id=1).favicon.name.startswith("organization_logos/1/favicon-")
