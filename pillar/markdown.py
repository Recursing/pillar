"""Bleached Markdown functionality.

This is for user-generated stuff, like comments.
"""

import bleach
import commonmark
import functools

from . import shortcodes

ALLOWED_TAGS = [
    'a',
    'abbr',
    'acronym',
    'b', 'strong',
    'i', 'em',
    'del', 'kbd',
    'dl', 'dt', 'dd',
    'blockquote',
    'code', 'pre',
    'li', 'ol', 'ul',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'p', 'br', 'hr',
    'sup', 'sub', 'strike',
    'img',
    'iframe',
    'video',
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'abbr': ['title'],
    'acronym': ['title'],
    'img': ['src', 'alt', 'width', 'height', 'title'],
    'iframe': ['src', 'width', 'height', 'frameborder', 'allowfullscreen'],
    'video': ['autoplay', 'controls', 'loop', 'muted', 'src'],
    '*': ['style'],
}

ALLOWED_STYLES = [
    'color', 'font-weight', 'background-color',
]

# Non-standard TLDS that bleach doesn't linkify:
# see https://github.com/mozilla/bleach/issues/519
EXTRA_TLDS = [
    "community",
    "chat",
    "today",
    "cloud",
    "fund",
    "to",
]

TLDS = bleach.linkifier.TLDS + EXTRA_TLDS
LINKIFY_FILTER = functools.partial(
    bleach.linkifier.LinkifyFilter, url_re=bleach.linkifier.build_url_re(tlds=TLDS)
)


def markdown(s: str) -> str:
    commented_shortcodes = shortcodes.comment_shortcodes(s)
    tainted_html = commonmark.commonmark(commented_shortcodes)

    # Create a Cleaner that supports parsing of bare links (see filters).
    cleaner = bleach.Cleaner(tags=ALLOWED_TAGS,
                             attributes=ALLOWED_ATTRIBUTES,
                             styles=ALLOWED_STYLES,
                             strip_comments=False,
                             filters=[LINKIFY_FILTER])

    safe_html = cleaner.clean(tainted_html)
    return safe_html


def cache_field_name(field_name: str) -> str:
    """Return the field name containing the cached HTML.

    See ValidateCustomFields._normalize_coerce_markdown().
    """
    return f'_{field_name}_html'
