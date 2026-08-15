import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import NextDelivery from '../../../platform/learners/components/NextDelivery';

vi.mock('../../render.jsx');

const localeMessages = {
  next_delivery: 'Next delivery',
  send_now: 'send now',
  sending: 'Sending...',
  content_send_failed: 'The content could not be sent.',
  delivery_no_longer_scheduled: 'This delivery is no longer scheduled.',
};

const nextDelivery = {
  delivery_schedule_id: 7,
  course_content_id: 3,
  course_content_title: 'Lesson Two',
  course_content_type: 'lesson',
  scheduled_at: '2026-08-20T09:00:00Z',
};

const sendUrl = '/api/organizations/1/enrollments/5/delivery-schedules/7/send/';

function renderComponent(props = {}) {
  return renderWithProviders(
    <NextDelivery
      nextDelivery={nextDelivery}
      sendUrl={sendUrl}
      canSend
      onSent={vi.fn()}
      {...props}
    />,
    { appContext: { localeMessages } }
  );
}

describe('NextDelivery', () => {
  it('renders nothing when there is no scheduled delivery', () => {
    const { container } = renderComponent({ nextDelivery: null });
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the scheduled time and the content title', () => {
    renderComponent();
    expect(screen.getByText(/Next delivery: 2026-08-20 09:00:00 — Lesson Two/)).toBeInTheDocument();
  });

  it('shows the send now link when the user may send', () => {
    renderComponent();
    expect(screen.getByRole('button', { name: /send now/i })).toBeInTheDocument();
  });

  it('hides the send now link when the user may not send', () => {
    renderComponent({ canSend: false });
    expect(screen.queryByRole('button', { name: /send now/i })).not.toBeInTheDocument();
    expect(screen.getByText(/Next delivery: 2026-08-20 09:00:00 — Lesson Two/)).toBeInTheDocument();
  });

  it('posts to the send endpoint and notifies the caller', async () => {
    const user = userEvent.setup();
    const onSent = vi.fn();
    renderComponent({ onSent });

    await user.click(screen.getByRole('button', { name: /send now/i }));

    await waitFor(() => expect(onSent).toHaveBeenCalled());
    const [url, options] = global.fetch.mock.calls[0];
    expect(url).toBe(sendUrl);
    expect(options.method).toBe('POST');
  });

  it('shows an error when the delivery is no longer scheduled', async () => {
    const user = userEvent.setup();
    const onSent = vi.fn();
    global.fetch.mockResolvedValue({
      ok: false,
      status: 409,
      json: () => Promise.resolve({ error: 'Delivery is no longer scheduled' }),
    });
    renderComponent({ onSent });

    await user.click(screen.getByRole('button', { name: /send now/i }));

    expect(await screen.findByText('This delivery is no longer scheduled.')).toBeInTheDocument();
    expect(onSent).not.toHaveBeenCalled();
    // The link comes back so the admin can retry once they know what happened.
    expect(screen.getByRole('button', { name: /send now/i })).toBeInTheDocument();
  });

  it('shows an error when sending fails', async () => {
    const user = userEvent.setup();
    global.fetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ error: 'Delivery failed' }),
    });
    renderComponent();

    await user.click(screen.getByRole('button', { name: /send now/i }));

    expect(await screen.findByText('The content could not be sent.')).toBeInTheDocument();
  });
});
