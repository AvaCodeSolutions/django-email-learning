import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { beforeAll, describe, expect, it } from 'vitest';

// The embed script is served as a raw JS string from Python
// (django_email_learning/public/embed_script.py), so the only way to cover its
// actual behaviour is to pull the template out and evaluate it here. The Python
// side can only assert on the source text, which is how a broken empty-image
// guard shipped once already.
const RELATIVE_SCRIPT_PATH = join('django_email_learning', 'public', 'embed_script.py');

// Walked up from the cwd rather than derived from import.meta.url, which Vite
// rewrites to a non-file URL.
function findEmbedScriptPath() {
    let directory = resolve(process.cwd());
    while (true) {
        const candidate = join(directory, RELATIVE_SCRIPT_PATH);
        if (existsSync(candidate)) {
            return candidate;
        }
        const parent = dirname(directory);
        if (parent === directory) {
            throw new Error(`Could not locate ${RELATIVE_SCRIPT_PATH} above ${process.cwd()}`);
        }
        directory = parent;
    }
}

function loadEmbedScript() {
    const source = readFileSync(findEmbedScriptPath(), 'utf8');
    const match = source.match(/_EMBED_SCRIPT_TEMPLATE = r"""([\s\S]*?)"""/);
    if (!match) {
        throw new Error('Could not extract _EMBED_SCRIPT_TEMPLATE from embed_script.py');
    }
    return match[1].replace('__API_BASE_JSON__', JSON.stringify('https://api.test/email_learning/embed/'));
}

function mountEnrollForm(attributes) {
    const element = document.createElement('del-enroll-form');
    element.setAttribute('token', 'tok');
    element.setAttribute('course_id', 'sample-course');
    Object.entries(attributes).forEach(([name, value]) => element.setAttribute(name, value));
    document.body.appendChild(element);
    return element;
}

describe('embed script del-enroll-form image handling', () => {
    beforeAll(() => {
        // eslint-disable-next-line no-new-func
        new Function(loadEmbedScript())();
    });

    it('registers both custom elements', () => {
        expect(customElements.get('del-enroll-form')).toBeTruthy();
        expect(customElements.get('del-newsletter-form')).toBeTruthy();
    });

    it('renders no image when course_image is absent', () => {
        // The "show course image" switch strips the attribute entirely, and a
        // course with no image never gets one. Neither may fall back to
        // resolving '' against the host page URL.
        const element = mountEnrollForm({});

        expect(element.shadowRoot.querySelector('img')).toBeNull();
    });

    it('renders no image when course_image is empty', () => {
        const element = mountEnrollForm({ course_image: '' });

        expect(element.shadowRoot.querySelector('img')).toBeNull();
    });

    it('renders no image when course_image is only whitespace', () => {
        const element = mountEnrollForm({ course_image: '   ' });

        expect(element.shadowRoot.querySelector('img')).toBeNull();
    });

    it('renders the image when course_image is a real http(s) url', () => {
        const element = mountEnrollForm({ course_image: 'https://cdn.test/course.jpg' });

        const image = element.shadowRoot.querySelector('img');
        expect(image).not.toBeNull();
        expect(image.getAttribute('src')).toBe('https://cdn.test/course.jpg');
        expect(image.className).toBe('course-image');
    });

    it('renders no image for non-http(s) course_image values', () => {
        expect(mountEnrollForm({ course_image: 'javascript:alert(1)' }).shadowRoot.querySelector('img')).toBeNull();
        expect(mountEnrollForm({ course_image: 'data:image/svg+xml,<svg/>' }).shadowRoot.querySelector('img')).toBeNull();
    });

    it('still renders the title and form when there is no image', () => {
        const element = mountEnrollForm({ course_title: 'Sample Course' });

        expect(element.shadowRoot.querySelector('img')).toBeNull();
        expect(element.shadowRoot.querySelector('.course-title').textContent).toBe('Sample Course');
        expect(element.shadowRoot.querySelector('form')).not.toBeNull();
    });
});
