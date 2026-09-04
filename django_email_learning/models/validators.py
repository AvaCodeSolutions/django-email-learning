"""Validators for human-facing name fields (Organization.name, Course.title).

These fields are rendered verbatim into emails - subject lines, ``From`` headers,
footers - so a value that carries a URL, breaks out of its line, or hides/reorders
text for the reader is a content-injection vector rather than a cosmetic problem.
Every check runs against the NFKC-normalized form so compatibility look-alikes
(fullwidth ``ｈｔｔｐ``) can't walk past the URL check.
"""

import re
import unicodedata

from django.core.exceptions import ValidationError

MAX_ORGANIZATION_NAME_LENGTH = 60

# A recognised TLD is what makes a bare "label.tld" read as a domain rather than
# as a course title ("Node.js") or an abbreviation ("Inc."). Explicit URLs - a
# scheme or a www. host - are caught below regardless of TLD.
_COMMON_TLDS = (
    "com net org io co edu gov mil info biz dev app ai me xyz online site tech "
    "store blog news live cloud link click page so sh gg tv fm to ly cc us uk "
    "ca au de fr es it nl se no fi dk ch at be ie nz jp cn in br ru za eu"
).split()

_URL_RE = re.compile(
    r"https?://"  # http:// or https://
    r"|://\S"  # any other scheme separator
    r"|\bwww\."  # www. host
    r"|[^\s./@]{2,}\.(?:" + "|".join(_COMMON_TLDS) + r")\b",  # bare domain
    re.IGNORECASE,
)

# Newlines, tabs, other C0/C1 control characters, and the Unicode line/paragraph
# separators. Never legitimate in a name, and what lets a value start a new
# header line in an email template.
_CONTROL_RE = re.compile("[\x00-\x1f\x7f-\x9f\u2028\u2029]")

# Zero-width and bidirectional-formatting characters: they hide text from a
# reviewer and reorder it for the reader. Spelled as escapes so the source file
# itself stays free of invisible characters.
_ZERO_WIDTH_BIDI_RE = re.compile(
    "["
    "\u200b-\u200f"  # zero-width space/(non-)joiner, LRM/RLM
    "\u202a-\u202e"  # bidi embeddings and overrides
    "\u2066-\u2069"  # bidi isolates
    "\u061c\u2060"  # Arabic letter mark, word joiner
    "\ufeff"  # zero-width no-break space / BOM
    "]"
)

# CJK scripts mix with each other (and Latin) in ordinary text; other scripts
# mixing is how a homoglyph attack smuggles a Cyrillic "о" into a Latin word.
_CJK_SCRIPTS = {"CJK", "HAN", "HIRAGANA", "KATAKANA", "HANGUL", "BOPOMOFO"}

# unicodedata has no script property; the first word of the character name is a
# good-enough proxy ("CYRILLIC SMALL LETTER A" -> "CYRILLIC").
_SCRIPT_ALIASES = {"IDEOGRAPHIC": "CJK", "KATAKANA-HIRAGANA": "KATAKANA"}


def _script_of(char: str) -> str | None:
    try:
        name = unicodedata.name(char)
    except ValueError:
        return None
    script = name.split(" ", 1)[0]
    return _SCRIPT_ALIASES.get(script, script)


def _check_mixed_scripts(value: str) -> None:
    scripts = {
        script
        for char in value
        if unicodedata.category(char).startswith("L")
        for script in (_script_of(char),)
        if script is not None
    }
    non_cjk = scripts - _CJK_SCRIPTS
    if len(non_cjk) > 1 or (non_cjk - {"LATIN"} and scripts & _CJK_SCRIPTS):
        raise ValidationError(
            "Name mixes characters from multiple scripts, which is not allowed.",
            code="mixed_scripts",
        )


def validate_safe_name(value: str) -> None:
    """Reject names that would be unsafe to render into an email.

    Shared by Organization.name and Course.title. Does not enforce a length
    limit - that stays per-field.
    """
    if not value:
        return

    normalized = unicodedata.normalize("NFKC", value)

    if _CONTROL_RE.search(value) or _CONTROL_RE.search(normalized):
        raise ValidationError(
            "Name may not contain newlines or control characters.",
            code="control_characters",
        )
    if _ZERO_WIDTH_BIDI_RE.search(value) or _ZERO_WIDTH_BIDI_RE.search(normalized):
        raise ValidationError(
            "Name may not contain zero-width or bidirectional formatting characters.",
            code="hidden_characters",
        )
    if _URL_RE.search(normalized):
        raise ValidationError(
            "Name may not contain a URL or web address.",
            code="url_in_name",
        )
    _check_mixed_scripts(normalized)


def validate_organization_name(value: str) -> None:
    if value and len(value) > MAX_ORGANIZATION_NAME_LENGTH:
        raise ValidationError(
            f"Name may be at most {MAX_ORGANIZATION_NAME_LENGTH} characters.",
            code="max_length",
        )
    validate_safe_name(value)
