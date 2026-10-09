import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import WaitingAtGate from '../../../platform/learners/components/WaitingAtGate';

vi.mock('../../render.jsx');

const localeMessages = {
  waiting_at_gate: 'Waiting at gate: %(gate)s',
  unlock_gate: 'Unlock',
  unlock_gate_title: 'Unlock this gate?',
  unlock_gate_confirmation: 'The learner moves past %(gate)s.',
  confirm_unlock_gate: 'Unlock',
  gate_unlock_failed: 'The gate could not be unlocked.',
};

const gate = { course_content_id: 7, title: 'Payment', key: 'payment' };
const unlockUrl = '/api/organizations/1/enrollments/5/gates/7/unlock/';

function renderComponent(props = {}) {
  return renderWithProviders(
    <WaitingAtGate gate={gate} unlockUrl={unlockUrl} canUnlock onUnlocked={vi.fn()} {...props} />,
    { appContext: { localeMessages } }
  );
}

/** The trigger and the confirm button share a label, so pick them apart by dialog. */
function confirmButton() {
  return screen.getByRole('dialog').querySelector('.MuiDialogActions-root button:last-of-type');
}

describe('WaitingAtGate', () => {
  beforeEach(() => {
    global.fetch.mockReset();
  });

  it('renders nothing when the learner is not waiting', () => {
    const { container } = renderComponent({ gate: null });
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the gate but no unlock action to a non-admin', () => {
    renderComponent({ canUnlock: false });

    expect(screen.getByText('Waiting at gate: Payment')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Unlock' })).not.toBeInTheDocument();
  });

  it('unlocks the gate after confirmation', async () => {
    const user = userEvent.setup();
    const onUnlocked = vi.fn();
    global.fetch.mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve({ status: 'unlocked' }) });
    renderComponent({ onUnlocked });

    await user.click(screen.getByRole('button', { name: 'Unlock' }));
    expect(screen.getByText('The learner moves past Payment.')).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
    await user.click(confirmButton());

    await waitFor(() => expect(onUnlocked).toHaveBeenCalled());
    const [url, options] = global.fetch.mock.calls[0];
    expect(url).toBe(unlockUrl);
    expect(options.method).toBe('POST');
  });

  it('keeps the confirmation open with an error when unlocking fails', async () => {
    const user = userEvent.setup();
    const onUnlocked = vi.fn();
    global.fetch.mockResolvedValue({ ok: false, status: 500, json: () => Promise.resolve({ error: 'boom' }) });
    renderComponent({ onUnlocked });

    await user.click(screen.getByRole('button', { name: 'Unlock' }));
    await user.click(confirmButton());

    expect(await screen.findByText('The gate could not be unlocked.')).toBeInTheDocument();
    expect(onUnlocked).not.toHaveBeenCalled();
  });
});
