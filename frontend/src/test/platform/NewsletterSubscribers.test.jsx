import { describe, it, expect, beforeEach, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import NewsletterSubscribers from '../../../platform/newsletter_subscribers/NewsletterSubscribers';

vi.mock('../../render.jsx');
vi.mock('vite/modulepreload-polyfill', () => ({}));

const localeMessages = {
  subscribers: 'Subscribers',
  email: 'Email',
  subscribed_at: 'Subscribed At',
  no_subscribers: 'No subscribers yet.',
  status: 'Status',
  confirmed: 'Confirmed',
  pending_confirmation: 'Pending confirmation',
  actions: 'Actions',
  export_csv: 'Export CSV',
};

const baseAppContext = {
  newsletterId: '3',
  newsletterTitle: 'Weekly Digest',
  organizationId: '1',
  isOrganizationAdmin: true,
  localeMessages,
};

describe('NewsletterSubscribers', () => {
  beforeEach(() => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/subscribers/?')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              items: [
                { id: 1, email: 'confirmed@example.com', subscribed_at: '2026-01-01T00:00:00Z', is_confirmed: true },
                { id: 2, email: 'pending@example.com', subscribed_at: '2026-01-02T00:00:00Z', is_confirmed: false },
              ],
              count: 2,
            }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('shows a "Confirmed" status for confirmed subscribers and "Pending confirmation" for unconfirmed ones', async () => {
    renderWithProviders(<NewsletterSubscribers />, { appContext: baseAppContext });

    expect(await screen.findByText('confirmed@example.com')).toBeInTheDocument();
    expect(screen.getByText('pending@example.com')).toBeInTheDocument();
    expect(screen.getByText('Confirmed')).toBeInTheDocument();
    expect(screen.getByText('Pending confirmation')).toBeInTheDocument();
  });
});
