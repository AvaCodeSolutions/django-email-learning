import { Node, mergeAttributes } from '@tiptap/core';
import { getReadableTextColor } from '../utils.js';

/**
 * The learner values a button's link can carry. Each is filled in per learner by the
 * server as the email is sent (see services/email_buttons.py), so only the parameter
 * names and which variable each one takes are stored in the content.
 */
export const LINK_VARIABLES = {
    enrollment_id: {
        label: 'Enrollment ID',
        description: "The learner's enrollment in this course. Your system can send it back to the unlock API to let them past a gate.",
        example: '1234',
    },
    email: {
        label: 'Learner email',
        description: "The learner's email address, so the page can recognise them or fill in a form.",
        example: 'learner@example.com',
    },
};

export const ALL_LINK_VARIABLES = Object.keys(LINK_VARIABLES);

export const PARAM_NAME_PATTERN = /^[A-Za-z0-9_.\-[\]]{1,64}$/;

/** `"client_reference_id=enrollment_id&email=email"` -> `[{ name, variable }]`, known variables only. */
export const parseQueryParams = (value) => Array.from(new URLSearchParams(value || '').entries())
    .filter(([, variable]) => variable in LINK_VARIABLES)
    .map(([name, variable]) => ({ name, variable }));

export const serializeQueryParams = (params) => new URLSearchParams(params.map(({ name, variable }) => [name, variable])).toString();

/** What the link looks like once it is sent, with example values in place of the learner's. */
export const exampleUrl = (href, params) => {
    try {
        const url = new URL(href);
        params.forEach(({ name, variable }) => url.searchParams.append(name, LINK_VARIABLES[variable].example));
        return url.toString();
    } catch {
        return '';
    }
};

const DEFAULT_BUTTON_COLOR = '#636eec';
// MUI's Edit icon, drawn without React since the node view is plain DOM.
const EDIT_ICON_PATH = 'M3 17.25V21h3.75L17.81 9.94l-3.75-3.75zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34a.996.996 0 0 0-1.41 0l-1.83 1.83 3.75 3.75z';

/**
 * A call-to-action button: a block-level link, stored as `<a data-email-button>` with the
 * learner values to add in `data-query-params`. It is a single unit in the editor - selected,
 * moved, aligned and deleted whole, and edited through its dialog rather than by typing into it.
 *
 * In the editor it is drawn as a plain element, not a link, so clicking it selects it rather
 * than following it. `brandColor` fills it as the email will; `onEdit(attributes)` is called
 * from the edit icon that shows on hover.
 */
export const EmailButton = Node.create({
    name: 'emailButton',
    group: 'block',
    atom: true,
    selectable: true,
    draggable: true,

    addOptions() {
        return { brandColor: DEFAULT_BUTTON_COLOR, onEdit: null };
    },

    addAttributes() {
        return {
            href: {
                default: '',
                parseHTML: (element) => element.getAttribute('href') || '',
            },
            label: {
                default: '',
                parseHTML: (element) => element.textContent || '',
                // Rendered as the link's text, not as an attribute.
                renderHTML: () => ({}),
            },
            queryParams: {
                default: '',
                parseHTML: (element) => element.getAttribute('data-query-params') || '',
                renderHTML: (attributes) => (attributes.queryParams ? { 'data-query-params': attributes.queryParams } : {}),
            },
        };
    },

    parseHTML() {
        // Above the Link mark's rule for `a[href]`, which would otherwise claim it as a plain link.
        return [{ tag: 'a[data-email-button]', priority: 100 }];
    },

    renderHTML({ node, HTMLAttributes }) {
        // HTMLAttributes carries the alignment TextAlign adds, as a text-align style.
        return ['a', mergeAttributes(HTMLAttributes, { 'data-email-button': '' }), node.attrs.label];
    },

    addNodeView() {
        return ({ node: initialNode, getPos, editor }) => {
            let node = initialNode;
            const background = /^#[0-9a-fA-F]{6}$/.test(this.options.brandColor || '') ? this.options.brandColor : DEFAULT_BUTTON_COLOR;

            const dom = document.createElement('div');
            dom.className = 'email-button-node';
            const body = document.createElement('span');
            body.className = 'email-button-node__body';
            const button = document.createElement('span');
            button.className = 'email-button-node__button';
            button.style.backgroundColor = background;
            button.style.color = getReadableTextColor(background);
            body.appendChild(button);

            if (editor.isEditable) {
                const edit = document.createElement('button');
                edit.type = 'button';
                edit.className = 'email-button-node__edit';
                edit.setAttribute('aria-label', 'Edit Button');
                edit.title = 'Edit Button';
                edit.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="${EDIT_ICON_PATH}"/></svg>`;
                edit.addEventListener('mousedown', (event) => event.preventDefault());
                edit.addEventListener('click', () => {
                    editor.chain().focus().setNodeSelection(getPos()).run();
                    this.options.onEdit?.(node.attrs);
                });
                body.appendChild(edit);
            }
            dom.appendChild(body);

            const render = () => {
                button.textContent = node.attrs.label;
                dom.style.textAlign = node.attrs.textAlign || 'center';
            };
            render();

            return {
                dom,
                update: (updated) => {
                    if (updated.type !== node.type) {
                        return false;
                    }
                    node = updated;
                    render();
                    return true;
                },
                // The edit icon handles its own clicks; the editor must not treat them as a selection.
                stopEvent: (event) => event.target instanceof Element && Boolean(event.target.closest('.email-button-node__edit')),
                ignoreMutation: () => true,
            };
        };
    },
});
