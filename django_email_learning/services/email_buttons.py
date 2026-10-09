"""Buttons in rich-text content, and the learner values their links carry.

The content editor stores a button as a plain link to the page the author typed:

    <a href="https://shop.example.com/pay" data-email-button=""
       data-query-params="client_reference_id=enrollment_id&amp;email=email">Pay now</a>

`data-query-params` maps a query parameter name to a link variable. The values are
filled in per recipient as each email is rendered - never stored - so the same lesson
can link every learner to the page with their own enrollment id, and the page that
opens knows who clicked.

Values are URL-encoded and appended to whatever query string the link already has.
A variable with no value for this email (there is no enrollment in a newsletter, or
in a lesson an admin sends to themselves) is left off rather than sent empty.
"""

import logging
import re
from html import escape, unescape
from html.parser import HTMLParser
from typing import Mapping, Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

ENROLLMENT_ID = "enrollment_id"
EMAIL = "email"
LINK_VARIABLES = frozenset({ENROLLMENT_ID, EMAIL})

BUTTON_ATTRIBUTE = "data-email-button"
QUERY_PARAMS_ATTRIBUTE = "data-query-params"

_PARAM_NAME = re.compile(r"^[A-Za-z0-9_.\-\[\]]{1,64}$")
_BLOCK_END = re.compile(r"</(?:p|h[1-6]|li|blockquote|pre)>|<br\s*/?>", re.IGNORECASE)
_BLANK_LINES = re.compile(r"\n{3,}")
_TEXT_ALIGN = re.compile(r"text-align:\s*(left|center|right)", re.IGNORECASE)
_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
DEFAULT_BUTTON_COLOR = "#636eec"


def link_variables(enrollment_id: Optional[int] = None, email: Optional[str] = None) -> dict[str, Optional[str]]:
    return {ENROLLMENT_ID: str(enrollment_id) if enrollment_id is not None else None, EMAIL: email}


def render_buttons(html: str, values: Mapping[str, Optional[str]], brand_color: Optional[str] = None) -> str:
    """`html` with each button made an email call-to-action linking with `values`.

    The button is filled with `brand_color` and keeps the alignment it was given in the
    editor, centred by default. Both are inline styles, since some email clients drop the
    stylesheet in the head.
    """
    if BUTTON_ATTRIBUTE not in html:
        return html
    return _ButtonRewriter(values, as_text=False, brand_color=brand_color).rewrite(html)


def readable_text_color(background: str) -> str:
    """Dark or white text, whichever reads better on `background` (YIQ brightness)."""
    red, green, blue = (int(background[i : i + 2], 16) for i in (1, 3, 5))
    return "#232936" if (red * 299 + green * 587 + blue * 114) / 1000 >= 135 else "#ffffff"


def render_as_text(html: str, values: Mapping[str, Optional[str]]) -> str:
    """`html` as plain text for an email's text alternative.

    Each button becomes "label: url" on a line of its own - stripping the markup alone
    would keep the label and lose the link - and block elements end their line.
    Entities are decoded, so the result is ready to send as it is and must not be
    HTML-escaped again.
    """
    if BUTTON_ATTRIBUTE in html:
        html = _ButtonRewriter(values, as_text=True).rewrite(html)
    text = unescape(strip_tags(_BLOCK_END.sub("\n", html)))
    return _BLANK_LINES.sub("\n\n", text).strip()


def button_url(href: str, query_params: str, values: Mapping[str, Optional[str]]) -> str:
    """`href` with the parameters `query_params` names appended, filled from `values`."""
    added = []
    for name, variable in parse_qsl(query_params, keep_blank_values=True):
        if not _PARAM_NAME.match(name) or variable not in LINK_VARIABLES:
            logger.warning(f"Ignoring button query parameter {name!r} for unknown variable {variable!r}.")
            continue
        value = values.get(variable)
        if value is None:
            continue
        added.append((name, value))
    if not added:
        return href
    parts = urlsplit(href)
    query = parse_qsl(parts.query, keep_blank_values=True) + added
    return urlunsplit(parts._replace(query=urlencode(query)))


class _ButtonRewriter(HTMLParser):
    """Re-emits sanitized HTML as it came, except for button links.

    Character references are kept as written (`convert_charrefs=False`), so text that
    passes through is not unescaped on the way.
    """

    def __init__(self, values: Mapping[str, Optional[str]], as_text: bool, brand_color: Optional[str] = None) -> None:
        super().__init__(convert_charrefs=False)
        self.values = values
        self.as_text = as_text
        self.color = brand_color if brand_color and _HEX_COLOR.match(brand_color) else DEFAULT_BUTTON_COLOR
        self.out: list[str] = []
        self.button_url: Optional[str] = None

    def rewrite(self, html: str) -> str:
        self.feed(html)
        self.close()
        return "".join(self.out)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attributes = dict(attrs)
        if tag == "a" and BUTTON_ATTRIBUTE in attributes and self.button_url is None:
            self.button_url = button_url(
                attributes.get("href") or "", attributes.get(QUERY_PARAMS_ATTRIBUTE) or "", self.values
            )
            if self.as_text:
                # On a line of its own, so the label and URL never run into the text around them.
                self.out.append("\n")
            else:
                align = _TEXT_ALIGN.search(attributes.get("style") or "")
                self.out.append(
                    f'<div class="email-cta-wrap" style="text-align: {align.group(1).lower() if align else "center"};">'
                    f'<a href="{escape(self.button_url, quote=True)}" class="email-cta" target="_blank" '
                    f'rel="noopener noreferrer" style="background-color: {self.color}; border-color: {self.color}; '
                    f'color: {readable_text_color(self.color)} !important;">'
                )
            return
        self.out.append(self.get_starttag_text() or "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.button_url is not None:
            self.out.append(f": {escape(self.button_url)}\n" if self.as_text else "</a></div>")
            self.button_url = None
            return
        self.out.append(f"</{tag}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        self.out.append(self.get_starttag_text() or "")

    def handle_data(self, data: str) -> None:
        self.out.append(data)

    def handle_entityref(self, name: str) -> None:
        self.out.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.out.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        self.out.append(f"<!--{data}-->")
