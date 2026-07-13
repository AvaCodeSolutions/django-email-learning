import bleach
from bleach.css_sanitizer import CSSSanitizer

# Tags/attributes the ContentEditor (TipTap) rich-text editor used for
# Lesson.content and Sendout.body can legitimately produce — either via its
# own toolbar (Bold, Italic, Link, BlockQuote, BulletList, Image, Heading
# levels 1-3, CodeBlock, TextAlign on paragraphs/headings) or via pasting
# already-formatted HTML, which TipTap preserves largely as-is. Anything
# else — script, iframe, on* attributes, javascript: URLs, arbitrary CSS —
# is stripped regardless of what a client sends, since the API is the real
# trust boundary, not the editor UI.
RICH_TEXT_ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "b",
    "em",
    "i",
    "a",
    "ul",
    "li",
    "img",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "blockquote",
    "pre",
    "code",
]
RICH_TEXT_ALLOWED_ATTRIBUTES = {
    "a": ["href", "target", "rel"],
    "img": ["src", "alt", "width", "height"],
    "p": ["style"],
    "h1": ["style"],
    "h2": ["style"],
    "h3": ["style"],
    "h4": ["style"],
    "h5": ["style"],
    "h6": ["style"],
}
# The only inline style TextAlign produces is text-align on paragraphs/
# headings — everything else (background-image, position, etc.) is dropped
# even though the style attribute itself is allowed above.
RICH_TEXT_CSS_SANITIZER = CSSSanitizer(allowed_css_properties=["text-align"])


def strip_html(value: str) -> str:
    """Remove all HTML markup, keeping only the text content.

    For fields with no legitimate HTML use case (plain titles/descriptions),
    so stored data can never contain executable markup regardless of how or
    where it's later rendered.
    """
    return bleach.clean(value, tags=[], attributes={}, strip=True)


def sanitize_rich_text(value: str) -> str:
    """Strip anything the rich-text editor doesn't legitimately produce.

    For fields where HTML is intentional (Lesson.content, Sendout.body).
    """
    return bleach.clean(
        value,
        tags=RICH_TEXT_ALLOWED_TAGS,
        attributes=RICH_TEXT_ALLOWED_ATTRIBUTES,
        css_sanitizer=RICH_TEXT_CSS_SANITIZER,
        strip=True,
    )
