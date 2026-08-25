import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import CancelEnrollment from '../../../platform/learners/components/CancelEnrollment';

vi.mock('../../render.jsx');

const localeMessages = {
  cancel_enrollment: 'Cancel enrollment',
  cancel_enrollment_title: 'Cancel this enrollment?',
  cancel_enrollment_confirmation: 'The learner stops receiving this course immediately.',
  keep_enrollment: 'Keep enrollment',
  confirm_cancel_enrollment: 'Cancel enrollment',
  canceling: 'Canceling...',
  enrollment_cancel_failed: 'The enrollment could not be canceled.',
};

const cancelUrl = '/api/organizations/1/enrollments/5/cancel/';

function renderComponent(props = {}) {
  return renderWithProviders(
    <CancelEnrollment
      status="active"
      cancelUrl={cancelUrl}
      canCancel
      onCanceled={vi.fn()}
      {...props}
    />,
    { appContext: { localeMessages } }
  );
}

/** The trigger and the confirm button share a label, so pick them apart by dialog. */
function confirmButton() {
  return screen.getByRole('dialog').querySelector('.MuiDialogActions-root button:last-of-type');
}

describe('CancelEnrollment', () => {
  it('renders nothing when the user may not cancel', () => {
    const { container } = renderComponent({ canCancel: false });
    expect(container).toBeEmptyDOMElement();
  });

  it.each(['completed', 'deactivated'])('renders nothing for a %s enrollment', (status) => {
    const { container } = renderComponent({ status });
    expect(container).toBeEmptyDOMElement();
  });

  it('offers the action for an unverified enrollment', () => {
    renderComponent({ status: 'unverified' });
    expect(screen.getByRole('button', { name: /cancel enrollment/i })).toBeInTheDocument();
  });

  it('asks for confirmation before cancelling anything', async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.click(screen.getByRole('button', { name: /cancel enrollment/i }));

    expect(await screen.findByText('Cancel this enrollment?')).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('cancels nothing when the admin backs out', async () => {
    const user = userEvent.setup();
    renderComponent();

    await user.click(screen.getByRole('button', { name: /cancel enrollment/i }));
    await user.click(await screen.findByRole('button', { name: 'Keep enrollment' }));

    await waitFor(() => expect(screen.queryByText('Cancel this enrollment?')).not.toBeInTheDocument());
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('posts to the cancel endpoint and notifies the caller', async () => {
    const user = userEvent.setup();
    const onCanceled = vi.fn();
    renderComponent({ onCanceled });

    await user.click(screen.getByRole('button', { name: /cancel enrollment/i }));
    await user.click(confirmButton());

    await waitFor(() => expect(onCanceled).toHaveBeenCalled());
    const [url, options] = global.fetch.mock.calls[0];
    expect(url).toBe(cancelUrl);
    expect(options.method).toBe('POST');
  });

  it('refreshes the view when the enrollment already ended', async () => {
    const user = userEvent.setup();
    const onCanceled = vi.fn();
    global.fetch.mockResolvedValue({
      ok: false,
      status: 409,
      json: () => Promise.resolve({ error: 'Enrollment can no longer be canceled', status: 'completed' }),
    });
    renderComponent({ onCanceled });

    await user.click(screen.getByRole('button', { name: /cancel enrollment/i }));
    await user.click(confirmButton());

    // Nothing was cancelled, but the dialog was showing stale data — reloading
    // is what tells the admin why the action did nothing.
    await waitFor(() => expect(onCanceled).toHaveBeenCalled());
    await waitFor(() => expect(screen.queryByText('Cancel this enrollment?')).not.toBeInTheDocument());
  });

  it('keeps the confirmation open with an error when cancelling fails', async () => {
    const user = userEvent.setup();
    const onCanceled = vi.fn();
    global.fetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ error: 'boom' }),
    });
    renderComponent({ onCanceled });

    await user.click(screen.getByRole('button', { name: /cancel enrollment/i }));
    await user.click(confirmButton());

    expect(await screen.findByText('The enrollment could not be canceled.')).toBeInTheDocument();
    expect(onCanceled).not.toHaveBeenCalled();
    expect(screen.getByText('Cancel this enrollment?')).toBeInTheDocument();
  });
});
