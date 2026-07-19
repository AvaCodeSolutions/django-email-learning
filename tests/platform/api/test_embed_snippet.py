from django_email_learning.platform.api.embed_snippet import build_embed_snippet


def test_build_embed_snippet_without_newsletter():
    html = build_embed_snippet(
        embed_enroll_url="https://example.com/api/public/embed/tok123/enrollments/",
        course_slug="my-course",
        newsletter_title=None,
    )
    assert "<label" not in html
    assert "https://example.com/api/public/embed/tok123/enrollments/" in html
    assert '"my-course"' in html
    assert 'type="email"' in html


def test_build_embed_snippet_with_newsletter():
    html = build_embed_snippet(
        embed_enroll_url="https://example.com/api/public/embed/tok123/enrollments/",
        course_slug="my-course",
        newsletter_title="Weekly Tips",
    )
    assert "<label" in html
    assert "Subscribe to Weekly Tips" in html
    assert 'name="subscribe_to_newsletter"' in html


def test_build_embed_snippet_escapes_html_in_newsletter_title():
    html = build_embed_snippet(
        embed_enroll_url="https://example.com/api/public/embed/tok123/enrollments/",
        course_slug="my-course",
        newsletter_title="<script>alert(1)</script>",
    )
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_build_embed_snippet_json_encodes_url_and_slug_for_js_context():
    # A slug/URL containing a quote must not be able to break out of the JS
    # string literal it's embedded in.
    html = build_embed_snippet(
        embed_enroll_url='https://example.com/enroll/"; alert(1); "',
        course_slug='slug"; alert(2); "',
        newsletter_title=None,
    )
    assert '"; alert(1); "' not in html.split("<script>")[1]
    assert '\\"' in html
