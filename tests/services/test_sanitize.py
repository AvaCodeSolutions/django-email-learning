from django_email_learning.services.sanitize import sanitize_rich_text, strip_html


def test_strip_html_removes_script_tag():
    assert strip_html("Nice course<script>alert(1)</script>") == "Nice coursealert(1)"


def test_strip_html_removes_event_handler_payload():
    assert strip_html('<img src=x onerror="alert(1)">') == ""


def test_strip_html_keeps_plain_text_unchanged():
    assert strip_html("5 is less than 10") == "5 is less than 10"


def test_sanitize_rich_text_keeps_allowed_formatting():
    value = "<p>Hello <strong>world</strong>, see <a href='https://example.com'>this</a>.</p>"
    result = sanitize_rich_text(value)
    assert "<strong>world</strong>" in result
    assert '<a href="https://example.com">this</a>' in result


def test_sanitize_rich_text_strips_script_tag():
    # The tag itself is removed (no longer executable); the inert text content
    # may remain, which is fine since it can no longer run as a script.
    result = sanitize_rich_text("<p>Hello</p><script>alert(document.cookie)</script>")
    assert "<script>" not in result
    assert "</script>" not in result


def test_sanitize_rich_text_strips_event_handler_attribute():
    result = sanitize_rich_text('<img src="x.png" onerror="alert(1)">')
    assert "onerror" not in result


def test_sanitize_rich_text_strips_iframe():
    result = sanitize_rich_text("<p>Hi</p><iframe src='https://evil.example'></iframe>")
    assert "<iframe" not in result


def test_sanitize_rich_text_keeps_blockquote():
    result = sanitize_rich_text("<blockquote><p>Quoted text</p></blockquote>")
    assert result == "<blockquote><p>Quoted text</p></blockquote>"


def test_sanitize_rich_text_keeps_code_block():
    result = sanitize_rich_text("<pre><code>pip install django-email-learning</code></pre>")
    assert result == "<pre><code>pip install django-email-learning</code></pre>"


def test_sanitize_rich_text_keeps_text_align_style():
    result = sanitize_rich_text('<p style="text-align: center;">Centered</p>')
    assert result == '<p style="text-align: center;">Centered</p>'


def test_sanitize_rich_text_strips_disallowed_css_properties():
    result = sanitize_rich_text('<p style="text-align: center; background-image: url(javascript:alert(1));">Hi</p>')
    assert "background-image" not in result
    assert "text-align: center" in result


def test_sanitize_rich_text_keeps_image_dimensions():
    result = sanitize_rich_text('<img src="https://example.com/logo.png" alt="Logo" width="195" height="202">')
    assert 'width="195"' in result
    assert 'height="202"' in result


def test_sanitize_rich_text_strips_arbitrary_class_attribute():
    result = sanitize_rich_text('<a href="https://example.com" class="ng-star-inserted">link</a>')
    assert "class" not in result
    assert 'href="https://example.com"' in result


def test_sanitize_rich_text_strips_javascript_href():
    result = sanitize_rich_text('<a href="javascript:alert(1)">click</a>')
    assert "javascript:" not in result


def test_sanitize_rich_text_strips_event_handler_on_blockquote():
    result = sanitize_rich_text('<blockquote onmouseover="alert(1)">quote</blockquote>')
    assert "onmouseover" not in result
