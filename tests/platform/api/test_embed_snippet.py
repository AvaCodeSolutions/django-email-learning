from django_email_learning.platform.api.embed_snippet import (
    build_embed_script_tag,
    build_embed_widget_tag,
)


def test_build_embed_script_tag():
    html = build_embed_script_tag("https://example.com/public/embed/del-enroll-form.js")
    assert html == '<script src="https://example.com/public/embed/del-enroll-form.js"></script>'


def test_build_embed_script_tag_escapes_url():
    html = build_embed_script_tag('https://example.com/"><script>alert(1)</script>')
    assert "<script>alert(1)</script>" not in html
    assert "&quot;" in html


def test_build_embed_widget_tag_without_newsletter():
    html = build_embed_widget_tag(token="tok123", course_slug="my-course", newsletter_title=None)
    assert html == '<del-enroll-form token="tok123" course_id="my-course"></del-enroll-form>'
    assert "news_letter_check" not in html


def test_build_embed_widget_tag_with_newsletter():
    html = build_embed_widget_tag(token="tok123", course_slug="my-course", newsletter_title="Weekly Tips")
    assert 'token="tok123"' in html
    assert 'course_id="my-course"' in html
    assert "news_letter_check" in html
    assert 'newsletter_title="Weekly Tips"' in html


def test_build_embed_widget_tag_escapes_newsletter_title():
    html = build_embed_widget_tag(token="tok123", course_slug="my-course", newsletter_title="<script>alert(1)</script>")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_build_embed_widget_tag_escapes_attribute_values():
    html = build_embed_widget_tag(
        token='tok"><script>alert(1)</script>',
        course_slug='slug"><script>alert(2)</script>',
        newsletter_title=None,
    )
    assert "<script>alert(1)</script>" not in html
    assert "<script>alert(2)</script>" not in html
    assert "&quot;" in html
