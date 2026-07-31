/**
 * URL sanitizers for values that reach the DOM.
 *
 * The app context is serialized by Django into the `#app-context` script tag and
 * a lot of it comes from data an organization admin controls (logo URLs, terms
 * of service link, uploaded file URLs) or from deployment settings. Putting any
 * of that straight into `href`, `src` or a `fetch()` target means a stored
 * `javascript:` or `data:text/html` URL becomes script execution on click.
 *
 * These helpers do not rewrite URLs - they either return the URL essentially
 * unchanged or return the fallback. That keeps relative URLs relative, so
 * concatenation like `apiBaseUrl + '/session'` behaves exactly as before.
 */

// Resolving against a fixed base rather than window.location keeps the result
// deterministic (tests, pages served from odd origins) while still letting
// `new URL` tell us which protocol a relative URL would inherit.
const RESOLUTION_BASE = 'https://sanitize-url.invalid/';

// Per the URL spec the parser removes ASCII tab and newlines from anywhere in
// the input, so `java\nscript:alert(1)` is a live javascript: URL. We remove
// exactly those, and nothing else: stripping characters the parser keeps would
// *create* dangerous URLs out of inert ones (a zero-width space inside
// `java<ZWSP>script:` is what keeps it harmless).
const TAB_OR_NEWLINE = /[\t\n\r]/g;

// Protocols for ordinary links. `http:`/`https:` also covers relative URLs,
// which inherit the base protocol.
const LINK_PROTOCOLS = new Set(['http:', 'https:', 'mailto:', 'tel:']);

// Endpoints we hand to fetch()/apiClient. Narrower than links: a mailto: or
// tel: base can only be a mistake or an attack.
const ENDPOINT_PROTOCOLS = new Set(['http:', 'https:']);

// Image sources. `blob:` covers locally-created object URLs; `data:` is allowed
// only for the raster image types matched below.
const IMAGE_PROTOCOLS = new Set(['http:', 'https:', 'blob:', 'data:']);

// SVG is deliberately excluded: it is inert in <img>, but the same URL tends to
// get reused in contexts where it is not.
const SAFE_IMAGE_DATA_URL = /^data:image\/(png|jpeg|jpg|gif|webp|avif|bmp|x-icon|vnd\.microsoft\.icon);/i;

// The URL parser strips leading and trailing "C0 control or space" (U+0000 to
// U+0020). Done by code point rather than a regexp so no control characters
// have to appear in this file.
function stripLeadingTrailingControls(value) {
    let start = 0;
    let end = value.length;
    while (start < end && value.charCodeAt(start) <= 0x20) {
        start += 1;
    }
    while (end > start && value.charCodeAt(end - 1) <= 0x20) {
        end -= 1;
    }
    return value.slice(start, end);
}

function clean(value) {
    if (typeof value !== 'string') {
        return null;
    }
    const cleaned = stripLeadingTrailingControls(value.replace(TAB_OR_NEWLINE, ''));
    return cleaned || null;
}

function protocolOf(cleaned) {
    try {
        return new URL(cleaned, RESOLUTION_BASE).protocol.toLowerCase();
    } catch {
        return null;
    }
}

function sanitize(value, allowedProtocols, fallback, extraCheck) {
    const cleaned = clean(value);
    if (cleaned === null) {
        return fallback;
    }
    const protocol = protocolOf(cleaned);
    if (protocol === null || !allowedProtocols.has(protocol)) {
        return fallback;
    }
    if (extraCheck && !extraCheck(cleaned, protocol)) {
        return fallback;
    }
    return cleaned;
}

/**
 * Sanitize a URL used as a link target (`href`, `window.location`, a URL shown
 * or copied to the clipboard). Allows http, https, mailto, tel and relative
 * URLs; anything else - `javascript:`, `data:`, `vbscript:`, `file:` - yields
 * the fallback.
 *
 * @param {unknown} value URL from the app context or an API response.
 * @param {string|undefined} [fallback] returned when the URL is unusable.
 * @returns {string|undefined}
 */
export function sanitizeUrl(value, fallback = '') {
    return sanitize(value, LINK_PROTOCOLS, fallback);
}

/**
 * Sanitize a URL used as an image source (`<img src>`, MUI `Avatar src`).
 * Allows http, https, blob, relative URLs and raster `data:image/*` URLs.
 *
 * Returns `undefined` by default because MUI renders a broken-image icon for
 * `src=""` but falls back to its placeholder for `src={undefined}`.
 *
 * @param {unknown} value URL from the app context or an API response.
 * @param {string|undefined} [fallback] returned when the URL is unusable.
 * @returns {string|undefined}
 */
export function sanitizeImageUrl(value, fallback = undefined) {
    return sanitize(value, IMAGE_PROTOCOLS, fallback, (cleaned, protocol) =>
        protocol !== 'data:' || SAFE_IMAGE_DATA_URL.test(cleaned),
    );
}

/**
 * Sanitize a URL - usually a base - that endpoints are built from and passed to
 * `fetch()` or `apiClient`. Allows http, https and relative URLs only.
 *
 * Sanitize the base rather than the concatenated string: the base is the part
 * that comes from the app context, and a `javascript:` base is what turns a
 * fetch target into a script URL if it later reaches an `href`.
 *
 * @param {unknown} value URL or base URL from the app context.
 * @param {string|undefined} [fallback] returned when the URL is unusable.
 * @returns {string|undefined}
 */
export function sanitizeEndpointUrl(value, fallback = '') {
    return sanitize(value, ENDPOINT_PROTOCOLS, fallback);
}
