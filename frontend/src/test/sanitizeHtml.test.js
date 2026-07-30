import { describe, expect, it } from 'vitest';
import { sanitizeComponentHtml, sanitizeHtml } from '../sanitizeHtml.js';

describe('sanitizeHtml', () => {
    it('keeps the markup translated messages actually use', () => {
        const html = 'I accept the <a href="https://example.com/terms">terms of service</a>.';

        expect(sanitizeHtml(html)).toBe(html);
    });

    it('keeps basic inline formatting', () => {
        expect(sanitizeHtml('You <strong>cannot</strong> create <em>more</em> courses')).toBe(
            'You <strong>cannot</strong> create <em>more</em> courses',
        );
    });

    it('strips script tags', () => {
        const result = sanitizeHtml('ok<script>alert(1)</script>');

        expect(result).not.toContain('<script');
        expect(result).not.toContain('alert(1)');
    });

    it('strips event handler attributes', () => {
        const result = sanitizeHtml('<img src="x" onerror="alert(1)">');

        expect(result).not.toContain('onerror');
    });

    it('strips javascript: urls', () => {
        const result = sanitizeHtml('<a href="javascript:alert(1)">click</a>');

        expect(result).not.toContain('javascript:');
    });

    it('drops custom elements, which are not expected in plain messages', () => {
        expect(sanitizeHtml('<my-widget></my-widget>')).not.toContain('my-widget');
    });

    it('returns an empty string for non-string input', () => {
        expect(sanitizeHtml(undefined)).toBe('');
        expect(sanitizeHtml(null)).toBe('');
    });
});

describe('sanitizeComponentHtml', () => {
    // The sidebar/dashboard slots are documented as taking a COMPONENT_TAG such
    // as `<your-component />`, so dropping custom elements here would break the
    // documented feature rather than harden it.
    it('keeps a custom element component tag', () => {
        expect(sanitizeComponentHtml('<your-component></your-component>')).toContain('your-component');
        expect(sanitizeComponentHtml('<my-notifications></my-notifications>')).toContain('my-notifications');
    });

    it('keeps the embed preview element with its attributes', () => {
        const html =
            '<del-enroll-form preview button_bg_color="#4A5EC0" token="tok" course_id="sample-course" ' +
            'course_title="Sample Course" news_letter_check newsletter_title="Weekly"></del-enroll-form>';

        const result = sanitizeComponentHtml(html);

        expect(result).toContain('del-enroll-form');
        expect(result).toContain('token="tok"');
        expect(result).toContain('course_id="sample-course"');
        expect(result).toContain('news_letter_check');
        expect(result).toContain('button_bg_color="#4A5EC0"');
    });

    it('still strips script tags', () => {
        const result = sanitizeComponentHtml('<my-widget></my-widget><script>alert(1)</script>');

        expect(result).toContain('my-widget');
        expect(result).not.toContain('<script');
    });

    it('strips event handlers on custom elements', () => {
        // Without the negative lookahead in the attribute name check, an
        // on* handler on a custom element satisfies the pattern and survives.
        const result = sanitizeComponentHtml('<my-widget onclick="alert(1)" onload="alert(2)"></my-widget>');

        expect(result).toContain('my-widget');
        expect(result).not.toContain('onclick');
        expect(result).not.toContain('onload');
        expect(result).not.toContain('alert');
    });

    it('strips javascript: urls inside a component slot', () => {
        const result = sanitizeComponentHtml('<a href="javascript:alert(1)">x</a>');

        expect(result).not.toContain('javascript:');
    });

    it('returns an empty string for non-string input', () => {
        expect(sanitizeComponentHtml(undefined)).toBe('');
        expect(sanitizeComponentHtml(null)).toBe('');
    });
});
