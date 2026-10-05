"""Which URL patterns the public organization and course pages live at.

The library serves them under its own include prefix (``<prefix>/public/@<slug>/``),
but a host project can mount the same views anywhere - at the site root, say - and
name its own routes in DJANGO_EMAIL_LEARNING["PUBLIC_URL_NAMES"]. Every public link
the library builds (Organization.public_url, Course.public_url, the JSON-LD on the
public pages, the platform's "public view" links) reverses these names, and the
public views redirect any other address they are reached at to the one named here.
"""

from django.conf import settings

DEFAULT_PUBLIC_URL_NAMES = {
    "organization": "django_email_learning:public:organization_page",
    "course": "django_email_learning:public:course_page",
}


def public_url_name(page: str) -> str:
    """The URL name to reverse for ``page`` ("organization" or "course"). The
    organization route takes an ``organization_slug`` kwarg; the course route
    takes ``organization_slug`` and ``course_slug``.
    """
    names = getattr(settings, "DJANGO_EMAIL_LEARNING", {}).get("PUBLIC_URL_NAMES") or {}
    return names.get(page) or DEFAULT_PUBLIC_URL_NAMES[page]
