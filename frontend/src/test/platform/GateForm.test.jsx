import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import GateForm from '../../../platform/course/components/GateForm';

vi.mock('../../render.jsx');
vi.mock('../../components/ContentEditor.jsx', () => ({
    default: ({ initialContent, contentUpdateCallback }) => (
        <textarea aria-label="Message editor" defaultValue={initialContent} onChange={(e) => contentUpdateCallback(e.target.value)} />
    ),
}));

const localeMessages = {
    title: 'Title',
    new_gate: 'New Gate',
    gate_key: 'Key',
    gate_timeout: 'Timeout',
    gate_timeout_action: 'When it times out',
    gate_timeout_continue: 'Continue past the gate',
    gate_key_invalid: 'Use only letters, numbers, hyphens and underscores.',
    save_gate: 'Save Gate',
    cancel: 'Cancel',
    days: 'Days',
    hours: 'Hours',
    period: 'Period',
};

const json = (body, status = 200) => Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) });

const renderForm = (props = {}, appContext = {}) => {
    window.localStorage.setItem('activeOrganizationId', '1');
    return renderWithProviders(
        <GateForm courseId={5} {...props} />,
        { appContext: { apiBaseUrl: '/api', localeMessages, userRole: 'editor', ...appContext } },
    );
};

const postCall = () => global.fetch.mock.calls.find(([, options]) => options?.method === 'POST');

describe('GateForm', () => {
    beforeEach(() => {
        global.fetch.mockClear();
        global.fetch.mockImplementation(() => json({ id: 9, gate: { id: 3 } }));
    });

    it('creates a gate whose key follows its title', async () => {
        const successCallback = vi.fn();
        const user = userEvent.setup();
        renderForm({ successCallback });

        await user.type(screen.getByLabelText(/Title/), 'Payment Received');
        expect(screen.getByLabelText(/Key/)).toHaveValue('payment-received');
        await user.type(screen.getByLabelText('Message editor'), '<p>Pay here</p>');
        await user.click(screen.getByRole('button', { name: 'Save Gate' }));

        await waitFor(() => expect(successCallback).toHaveBeenCalled());
        const [url, options] = postCall();
        expect(url).toBe('/api/organizations/1/courses/5/contents/');
        expect(JSON.parse(options.body)).toEqual({
            content: {
                type: 'gate',
                title: 'Payment Received',
                key: 'payment-received',
                message: '<p>Pay here</p>',
                unlocked_subject: '',
                unlocked_message: '',
                timeout_days: 0,
                timeout_action: 'deactivate',
            },
            waiting_period: { period: 1, type: 'hours' },
        });
    });

    it('stops following the title once the key is edited', async () => {
        const user = userEvent.setup();
        renderForm();

        await user.type(screen.getByLabelText(/Key/), 'pay');
        await user.type(screen.getByLabelText(/Title/), 'Payment');

        expect(screen.getByLabelText(/Key/)).toHaveValue('pay');
    });

    it('refuses a key that is not a slug', async () => {
        const user = userEvent.setup();
        renderForm();

        await user.type(screen.getByLabelText(/Title/), 'Payment');
        await user.clear(screen.getByLabelText(/Key/));
        await user.type(screen.getByLabelText(/Key/), 'has space');
        await user.click(screen.getByRole('button', { name: 'Save Gate' }));

        expect(screen.getByText(localeMessages.gate_key_invalid)).toBeInTheDocument();
        expect(postCall()).toBeUndefined();
    });

    it('sends an emptied message as no message', async () => {
        const user = userEvent.setup();
        renderForm({ contentId: 9, initialTitle: 'Payment', initialKey: 'payment', initialMessage: '<p>Old</p>' });

        await user.clear(screen.getByLabelText('Message editor'));
        await user.type(screen.getByLabelText('Message editor'), '<p></p>');
        await user.click(screen.getByRole('button', { name: 'Save Gate' }));

        await waitFor(() => expect(postCall()).toBeDefined());
        const [url, options] = postCall();
        expect(url).toBe('/api/organizations/1/courses/5/contents/9/');
        expect(JSON.parse(options.body).gate.message).toBe('');
    });

    it('sends a timeout and its action when the timeout is on', async () => {
        const user = userEvent.setup();
        renderForm({ contentId: 9, initialTitle: 'Payment', initialKey: 'payment' });

        await user.click(screen.getByRole('switch', { name: 'Timeout' }));
        await user.click(screen.getByRole('combobox', { name: 'When it times out' }));
        await user.click(screen.getByRole('option', { name: 'Continue past the gate' }));
        await user.click(screen.getByRole('button', { name: 'Save Gate' }));

        await waitFor(() => expect(postCall()).toBeDefined());
        const gate = JSON.parse(postCall()[1].body).gate;
        expect(gate.timeout_days).toBe(14);
        expect(gate.timeout_action).toBe('continue');
    });

    it('sends an unlocked message and its subject once switched on', async () => {
        const user = userEvent.setup();
        renderForm({ contentId: 9, initialTitle: 'Payment', initialKey: 'payment' });

        await user.click(screen.getByRole('switch', { name: 'Email learners when the gate unlocks' }));
        await user.type(screen.getByLabelText('Subject'), " You're in ");
        await user.type(screen.getAllByLabelText('Message editor')[1], '<p>Thanks</p>');
        await user.click(screen.getByRole('button', { name: 'Save Gate' }));

        await waitFor(() => expect(postCall()).toBeDefined());
        const gate = JSON.parse(postCall()[1].body).gate;
        expect(gate.unlocked_subject).toBe("You're in");
        expect(gate.unlocked_message).toBe('<p>Thanks</p>');
    });

    it('clears the unlocked message when switched off', async () => {
        const user = userEvent.setup();
        renderForm({
            contentId: 9, initialTitle: 'Payment', initialKey: 'payment',
            initialUnlockedSubject: 'Paid', initialUnlockedMessage: '<p>Thanks</p>',
        });

        const toggle = screen.getByRole('switch', { name: 'Email learners when the gate unlocks' });
        expect(toggle).toBeChecked();
        await user.click(toggle);
        await user.click(screen.getByRole('button', { name: 'Save Gate' }));

        await waitFor(() => expect(postCall()).toBeDefined());
        const gate = JSON.parse(postCall()[1].body).gate;
        expect(gate.unlocked_subject).toBe('');
        expect(gate.unlocked_message).toBe('');
    });

    it('renders gate editor components with the gate they act on', () => {
        const { container } = renderForm(
            { contentId: 9, initialTitle: 'Payment', initialKey: 'payment' },
            { gateEditorComponents: [{ tagName: 'stripe-gate-payment' }, { tagName: 'img onerror' }] },
        );

        const element = container.querySelector('stripe-gate-payment');
        expect(element).not.toBeNull();
        expect(element.getAttribute('organization-id')).toBe('1');
        expect(element.getAttribute('course-id')).toBe('5');
        expect(element.getAttribute('content-id')).toBe('9');
        expect(element.getAttribute('can-edit')).toBe('true');
        expect(container.querySelector('img')).toBeNull();
    });

    it('gives gate editor components no content id before the gate is saved', () => {
        const { container } = renderForm({}, { gateEditorComponents: [{ tagName: 'stripe-gate-payment' }] });

        expect(container.querySelector('stripe-gate-payment').hasAttribute('content-id')).toBe(false);
    });
});
