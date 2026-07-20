from django.utils.html import escape


def build_embed_script_tag(script_url: str) -> str:
    """The one-time <script> tag that loads the shared, deployment-generic
    del-enroll-form custom element definition (django_email_learning.public.embed_script).
    Goes once anywhere on the page (e.g. a shared footer/header template).
    """
    return f'<script src="{escape(script_url)}"></script>'


def build_embed_widget_tag(
    *,
    token: str,
    course_slug: str,
    course_title: str,
    course_image_url: str | None,
    newsletter_title: str | None,
) -> str:
    """Builds the <del-enroll-form> placeholder tag that pairs with
    build_embed_script_tag(). Meant to be placed wherever the organization
    wants the enrollment form to appear, and repeated for multiple placements
    (each with its own course_id).

    course_title/course_image_url are always attached when available - it's
    up to the caller's UI (e.g. the "show course title"/"show image"
    switches in the platform embed dialog) whether to strip them back out of
    what's actually shown/copied.

    All values land in HTML attributes/text, escaped via Django's escape() -
    the only encoding needed since (unlike the old inline-script design) none
    of this is embedded in JS anymore.
    """
    attrs = [
        f'token="{escape(token)}"',
        f'course_id="{escape(course_slug)}"',
        f'course_title="{escape(course_title)}"',
    ]
    if course_image_url:
        attrs.append(f'course_image="{escape(course_image_url)}"')
    if newsletter_title:
        attrs.append("news_letter_check")
        attrs.append(f'newsletter_title="{escape(newsletter_title)}"')

    return f"<del-enroll-form {' '.join(attrs)}></del-enroll-form>"
