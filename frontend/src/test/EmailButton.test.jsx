import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from './test-utils';
import ContentEditor from '../components/ContentEditor';
import EmailButtonDialog from '../components/EmailButtonDialog';
import { exampleUrl, parseQueryParams, serializeQueryParams } from '../components/emailButton';

vi.mock('../render.jsx');

const renderDialog = (props = {}) => {
    const onSave = vi.fn();
    renderWithProviders(
        <EmailButtonDialog open button={null} variables={['enrollment_id', 'email']} onSave={onSave} onClose={vi.fn()} {...props} />
    );
    return onSave;
};

describe('emailButton helpers', () => {
    it('round-trips query parameters and drops unknown variables', () => {
        const params = parseQueryParams('client_reference_id=enrollment_id&email=email&x=password');
        expect(params).toEqual([
            { name: 'client_reference_id', variable: 'enrollment_id' },
            { name: 'email', variable: 'email' },
        ]);
        expect(serializeQueryParams(params)).toBe('client_reference_id=enrollment_id&email=email');
    });

    it('builds an example link that keeps the existing query', () => {
        expect(exampleUrl('https://shop.example.com/pay?plan=pro', [{ name: 'email', variable: 'email' }]))
            .toBe('https://shop.example.com/pay?plan=pro&email=learner%40example.com');
    });
});

describe('EmailButtonDialog', () => {
    it('inserts a button whose link carries the chosen details', async () => {
        const user = userEvent.setup();
        const onSave = renderDialog();

        await user.type(screen.getByLabelText('Button text'), 'Pay now');
        await user.type(screen.getByLabelText('Link'), 'https://shop.example.com/pay');
        await user.click(screen.getByRole('checkbox', { name: 'Enrollment ID' }));
        const name = screen.getByLabelText('Parameter name');
        await user.clear(name);
        await user.type(name, 'client_reference_id');

        expect(screen.getByTestId('email-button-preview')).toHaveTextContent(
            'https://shop.example.com/pay?client_reference_id=1234'
        );
        await user.click(screen.getByRole('button', { name: 'Insert' }));

        expect(onSave).toHaveBeenCalledWith({
            label: 'Pay now',
            href: 'https://shop.example.com/pay',
            queryParams: 'client_reference_id=enrollment_id',
        });
    });

    it('explains what adding learner details does', () => {
        renderDialog();

        expect(screen.getByText(/each learner's own details are added to the end of the link/)).toBeInTheDocument();
        expect(screen.getByText(/send it back to the unlock API/)).toBeInTheDocument();
    });

    it('offers only the details the content has', () => {
        renderDialog({ variables: ['email'] });

        expect(screen.getByRole('checkbox', { name: 'Learner email' })).toBeInTheDocument();
        expect(screen.queryByRole('checkbox', { name: 'Enrollment ID' })).not.toBeInTheDocument();
    });

    it('refuses a link that is not a web address', async () => {
        const user = userEvent.setup();
        const onSave = renderDialog();

        await user.type(screen.getByLabelText('Button text'), 'Pay');
        await user.type(screen.getByLabelText('Link'), 'javascript:alert(1)');
        await user.click(screen.getByRole('button', { name: 'Insert' }));

        expect(screen.getByText(/Enter a full web address/)).toBeInTheDocument();
        expect(onSave).not.toHaveBeenCalled();
    });

    it('refuses two details with the same parameter name', async () => {
        const user = userEvent.setup();
        const onSave = renderDialog();

        await user.type(screen.getByLabelText('Button text'), 'Pay');
        await user.type(screen.getByLabelText('Link'), 'https://shop.example.com');
        await user.click(screen.getByRole('checkbox', { name: 'Enrollment ID' }));
        await user.click(screen.getByRole('checkbox', { name: 'Learner email' }));
        const [first] = screen.getAllByLabelText('Parameter name');
        await user.clear(first);
        await user.type(first, 'email');
        await user.click(screen.getByRole('button', { name: 'Insert' }));

        expect(screen.getAllByText('Each detail needs its own parameter name.')).toHaveLength(2);
        expect(onSave).not.toHaveBeenCalled();
    });

    it('opens an existing button with its details', () => {
        renderDialog({
            button: { label: 'Pay', href: 'https://shop.example.com', queryParams: 'prefilled_email=email' },
            onRemove: vi.fn(),
        });

        expect(screen.getByLabelText('Button text')).toHaveValue('Pay');
        expect(screen.getByRole('checkbox', { name: 'Learner email' })).toBeChecked();
        expect(screen.getByRole('checkbox', { name: 'Enrollment ID' })).not.toBeChecked();
        expect(screen.getByLabelText('Parameter name')).toHaveValue('prefilled_email');
        expect(screen.getByRole('button', { name: 'Remove' })).toBeInTheDocument();
    });
});

describe('ContentEditor buttons', () => {
    const saved = '<p>Hi</p><a href="https://shop.example.com/pay" data-email-button="" data-query-params="client_reference_id=enrollment_id">Pay now</a>';

    it('keeps a saved button as it was', async () => {
        let editor;
        renderWithProviders(
            <ContentEditor initialContent={saved} contentUpdateCallback={vi.fn()} editorInstanceCallback={(instance) => { editor = instance; }} />
        );

        await waitFor(() => expect(editor).toBeTruthy());
        const html = editor.getHTML();
        expect(html).toContain('data-email-button=""');
        expect(html).toContain('data-query-params="client_reference_id=enrollment_id"');
        expect(html).toContain('href="https://shop.example.com/pay"');
        expect(html).toContain('>Pay now</a>');
    });

    it('inserts a button from the toolbar', async () => {
        const user = userEvent.setup();
        const contentUpdateCallback = vi.fn();
        renderWithProviders(<ContentEditor initialContent="<p>Hi</p>" contentUpdateCallback={contentUpdateCallback} />);

        await user.click(await screen.findByRole('button', { name: 'Insert Button' }));
        const dialog = screen.getByRole('dialog');
        await user.type(within(dialog).getByLabelText('Button text'), 'Pay now');
        await user.type(within(dialog).getByLabelText('Link'), 'https://shop.example.com/pay');
        await user.click(within(dialog).getByRole('checkbox', { name: 'Learner email' }));
        await user.click(within(dialog).getByRole('button', { name: 'Insert' }));

        await waitFor(() => expect(contentUpdateCallback).toHaveBeenCalled());
        const html = contentUpdateCallback.mock.calls.at(-1)[0];
        const button = new DOMParser().parseFromString(html, 'text/html').querySelector('a[data-email-button]');
        expect(button.getAttribute('href')).toBe('https://shop.example.com/pay');
        expect(button.getAttribute('data-query-params')).toBe('email=email');
        expect(button.textContent).toBe('Pay now');
    });
});

describe('ContentEditor button display', () => {
    const saved = '<a href="https://shop.example.com/pay" data-email-button="">Pay now</a>';

    const renderEditor = (props = {}, appContext = {}) => {
        let editor;
        const result = renderWithProviders(
            <ContentEditor initialContent={saved} contentUpdateCallback={vi.fn()} editorInstanceCallback={(instance) => { editor = instance; }} {...props} />,
            { appContext: { brandColor: '#f5c518', ...appContext } }
        );
        return { ...result, getEditor: () => editor };
    };

    it('draws the button in the brand colour, not as a link', async () => {
        const { container } = renderEditor();

        const button = await waitFor(() => {
            const element = container.querySelector('.email-button-node__button');
            expect(element).toBeTruthy();
            return element;
        });
        expect(button).toHaveTextContent('Pay now');
        expect(button.closest('a')).toBeNull();
        expect(container.querySelector('.tiptap a[href="https://shop.example.com/pay"]')).toBeNull();
        expect(button).toHaveStyle({ backgroundColor: '#f5c518', color: '#232936' });
    });

    it('opens the button from its edit icon', async () => {
        const user = userEvent.setup();
        renderEditor();

        await user.click(await screen.findByRole('button', { name: 'Edit Button' }));

        const dialog = screen.getByRole('dialog');
        expect(within(dialog).getByLabelText('Button text')).toHaveValue('Pay now');
        await user.clear(within(dialog).getByLabelText('Button text'));
        await user.type(within(dialog).getByLabelText('Button text'), 'Pay today');
        await user.click(within(dialog).getByRole('button', { name: 'Save' }));

        expect(await screen.findByText('Pay today')).toBeInTheDocument();
    });

    it('offers no edit icon when the editor is read-only', async () => {
        const { container } = renderEditor({ disabled: true });

        await waitFor(() => expect(container.querySelector('.email-button-node__button')).toBeTruthy());
        expect(screen.queryByRole('button', { name: 'Edit Button' })).not.toBeInTheDocument();
    });

    it('aligns a selected button and stores the alignment', async () => {
        const { getEditor, container } = renderEditor();
        await waitFor(() => expect(getEditor()).toBeTruthy());
        const editor = getEditor();

        editor.chain().setNodeSelection(0).setTextAlign('right').run();

        expect(editor.getHTML()).toContain('style="text-align: right;"');
        await waitFor(() => expect(container.querySelector('.email-button-node')).toHaveStyle({ textAlign: 'right' }));
    });

    it('centres a button that has no alignment', async () => {
        const { container } = renderEditor();

        await waitFor(() => expect(container.querySelector('.email-button-node')).toHaveStyle({ textAlign: 'center' }));
    });
});
