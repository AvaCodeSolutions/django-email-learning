import DOMPurify from 'dompurify';

// Custom element names: at least one hyphen, per the HTML spec. Deliberately
// permissive about which element, since the tag comes from the deployment's own
// SIDEBAR / DASHBOARD.CUSTOM_COMPONENTS settings and we can't know its name.
const CUSTOM_ELEMENT_NAME = /^[a-z][a-z0-9]*(-[a-z0-9]+)+$/;

// Attributes on those custom elements. The negative lookahead is the important
// part: without it an `onclick` on a custom element would satisfy the name check
// and survive sanitization.
const CUSTOM_ELEMENT_ATTRIBUTE = /^(?!on)[a-z][a-z0-9_-]*$/;

const CUSTOM_ELEMENT_HANDLING = {
    tagNameCheck: CUSTOM_ELEMENT_NAME,
    attributeNameCheck: CUSTOM_ELEMENT_ATTRIBUTE,
    allowCustomizedBuiltInElements: false,
};

/**
 * Sanitize ordinary markup - translated strings with links, short messages.
 * Custom elements are not expected here and are dropped.
 */
export function sanitizeHtml(html) {
    if (typeof html !== 'string') {
        return '';
    }
    return DOMPurify.sanitize(html);
}

/**
 * Sanitize markup that is expected to contain a custom element: the sidebar and
 * dashboard custom component slots (documented as `COMPONENT_TAG`, e.g.
 * `<your-component />`) and the `<del-enroll-form>` embed preview.
 *
 * DOMPurify drops unknown elements by default, so these need
 * CUSTOM_ELEMENT_HANDLING or the feature breaks. Scripts, event handlers and
 * javascript:/data: URLs are still stripped.
 */
export function sanitizeComponentHtml(html) {
    if (typeof html !== 'string') {
        return '';
    }
    return DOMPurify.sanitize(html, { CUSTOM_ELEMENT_HANDLING });
}
