import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import WaitingForConfirmation from '../../../platform/learners/components/WaitingForConfirmation';

vi.mock('../../render.jsx');

const localeMessages = {
    waiting_for_confirmation: 'Waiting at the enrollment gate',
    confirm_enrollment: 'Confirm enrollment',
    enrollment_confirm_failed: 'The enrollment could not be confirmed.',
    verify_enrollment: 'Verify enrollment',
};
const confirmUrl = '/api/organizations/1/enrollments/5/confirm/';

function renderComponent(props = {}) {
    return renderWithProviders(
        <WaitingForConfirmation confirmUrl={confirmUrl} canConfirm onConfirmed={vi.fn()} {...props} />,
        { appContext: { localeMessages } }
    );
}

function confirmButton() {
    return screen.getByRole('dialog').querySelector('.MuiDialogActions-root button:last-of-type');
}

describe('WaitingForConfirmation', () => {
    beforeEach(() => {
        global.fetch.mockReset();
    });

    it('shows the wait but no action to a non-admin', () => {
        renderComponent({ canConfirm: false });

        expect(screen.getByText('Waiting at the enrollment gate')).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Confirm enrollment' })).not.toBeInTheDocument();
    });

    it('confirms the enrollment after asking', async () => {
        global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ status: 'confirmed' }) });
        const onConfirmed = vi.fn();
        const user = userEvent.setup();
        renderComponent({ onConfirmed });

        await user.click(screen.getByRole('button', { name: 'Confirm enrollment' }));
        await user.click(confirmButton());

        await waitFor(() => expect(onConfirmed).toHaveBeenCalled());
        const [url, options] = global.fetch.mock.calls[0];
        expect(url).toBe(confirmUrl);
        expect(options.method).toBe('POST');
    });

    it('reports a failure without closing', async () => {
        global.fetch.mockResolvedValue({ ok: false, status: 500, json: () => Promise.resolve({ error: 'boom' }) });
        const user = userEvent.setup();
        renderComponent();

        await user.click(screen.getByRole('button', { name: 'Confirm enrollment' }));
        await user.click(confirmButton());

        expect(await screen.findByText('The enrollment could not be confirmed.')).toBeInTheDocument();
    });

    it('offers to verify an enrollment in a course confirmed by link, without the gate label', async () => {
        global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ status: 'confirmed' }) });
        const onConfirmed = vi.fn();
        const user = userEvent.setup();
        renderComponent({ gated: false, onConfirmed });

        expect(screen.queryByText('Waiting at the enrollment gate')).not.toBeInTheDocument();
        await user.click(screen.getByRole('button', { name: 'Verify enrollment' }));
        await user.click(confirmButton());

        await waitFor(() => expect(onConfirmed).toHaveBeenCalled());
        expect(global.fetch.mock.calls[0][0]).toBe(confirmUrl);
    });

    it('shows nothing to a non-admin for a course confirmed by link', () => {
        const { container } = renderComponent({ gated: false, canConfirm: false });

        expect(container).toBeEmptyDOMElement();
    });
});
