import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import ApiKeys from '../../../platform/settings_api_keys/ApiKeys';

vi.mock('../../render.jsx');

vi.mock('@mui/material', async () => ({
  ...(await vi.importActual('@mui/material')),
  useMediaQuery: vi.fn(() => true),
}));

function setupFetch(apiKeys = []) {
  global.fetch.mockImplementation((url) => {
    if (url.includes('/api_keys/')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ api_keys: apiKeys }),
      });
    }
    if (url.includes('/status/jobs/')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ jobs: { deliver_contents: null } }),
      });
    }
    if (url.includes('/organizations/')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ organizations: [] }),
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
  });
}

const activeKey = {
  id: '1',
  key_id: 'a1b2c3d4e5f6',
  name: 'CI runner',
  key_type: 'platform',
  scopes: [],
  created_by: 'admin',
  created_at: '2024-01-01',
  expires_at: null,
  revoked_at: null,
  last_used_at: null,
};

const localeMessages = {
  api_keys: 'API Keys',
  api_key_intro: 'Use API keys to access the API.',
  add_api_key: 'Add API Key',
  key_id: 'Key ID',
  name: 'Name',
  status: 'Status',
  active: 'Active',
  revoked: 'Revoked',
  expired: 'Expired',
  last_used: 'Last Used',
  never_used: 'Never used',
  created_by: 'Created By',
  created_at: 'Created At',
  actions: 'Actions',
  copy: 'Copy',
  copied: 'Copied',
  done: 'Done',
  new_api_key_created: 'New API key created',
  copy_key_now_warning: 'Copy this key now. It cannot be shown again.',
  confirm_revocation: 'Confirm Revocation',
  are_you_sure_revoke_key: 'Are you sure you want to revoke this API key?',
  cancel: 'Cancel',
  revoke: 'Revoke',
  no_api_keys_found: 'No API keys yet.',
  organizations: 'Organizations',
  course_management: 'Courses',
  learners: 'Learners',
  content_delivery_tooltip: 'Content delivery',
  content_delivery_job: 'Content delivery',
  last_run: 'Last run:',
  never_run: 'Never run',
  upload_button_label: 'Upload',
  uploaded_image_alt: 'Uploaded image',
  remove_image: 'Remove',
};

describe('ApiKeys', () => {
  beforeEach(() => {
    setupFetch();
  });

  it('renders the intro text', async () => {
    renderWithProviders(<ApiKeys />, {
      appContext: { localeMessages, isPlatformAdmin: true },
    });
    await waitFor(() =>
      expect(screen.getByText('Use API keys to access the API.')).toBeInTheDocument()
    );
  });

  it('renders the Add API Key button', async () => {
    renderWithProviders(<ApiKeys />, {
      appContext: { localeMessages, isPlatformAdmin: true },
    });
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Add API Key/ })).toBeInTheDocument()
    );
  });

  it('shows the key id and metadata after loading keys', async () => {
    setupFetch([activeKey]);
    renderWithProviders(<ApiKeys />, {
      appContext: { localeMessages, isPlatformAdmin: true },
    });
    await waitFor(() => expect(screen.getByText('admin')).toBeInTheDocument());
    expect(screen.getByText('a1b2c3d4e5f6')).toBeInTheDocument();
    expect(screen.getByText('2024-01-01')).toBeInTheDocument();
    expect(screen.getByText('Never used')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('marks a revoked key as revoked and offers no revoke action', async () => {
    setupFetch([{ ...activeKey, revoked_at: '2024-02-01' }]);
    renderWithProviders(<ApiKeys />, {
      appContext: { localeMessages, isPlatformAdmin: true },
    });
    await waitFor(() => expect(screen.getByText('Revoked')).toBeInTheDocument());
    expect(
      screen.queryAllByRole('button').find((btn) => btn.querySelector('[data-testid="DeleteIcon"]'))
    ).toBeUndefined();
  });

  it('marks a key past its expiry as expired', async () => {
    setupFetch([{ ...activeKey, expires_at: '2020-01-01T00:00:00Z' }]);
    renderWithProviders(<ApiKeys />, {
      appContext: { localeMessages, isPlatformAdmin: true },
    });
    await waitFor(() => expect(screen.getByText('Expired')).toBeInTheDocument());
  });

  it('shows the token once after creating a key', async () => {
    const user = userEvent.setup();
    global.fetch.mockImplementation((url, options) => {
      if (url.includes('/api_keys/') && options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ ...activeKey, id: '2', token: 'elk_abc123_supersecret' }),
        });
      }
      if (url.includes('/api_keys/')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ api_keys: [] }),
        });
      }
      if (url.includes('/status/jobs/')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ jobs: { deliver_contents: null } }) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ organizations: [] }) });
    });
    renderWithProviders(<ApiKeys />, {
      appContext: { localeMessages, isPlatformAdmin: true },
    });
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Add API Key/ })).toBeInTheDocument()
    );
    await user.click(screen.getByRole('button', { name: /Add API Key/ }));

    await waitFor(() => expect(screen.getByText('New API key created')).toBeInTheDocument());
    expect(screen.getByTestId('new-api-key-token')).toHaveTextContent('elk_abc123_supersecret');
    expect(screen.getByText('Copy this key now. It cannot be shown again.')).toBeInTheDocument();
  });

  it('never renders a token for keys returned by the listing', async () => {
    setupFetch([activeKey]);
    renderWithProviders(<ApiKeys />, {
      appContext: { localeMessages, isPlatformAdmin: true },
    });
    await waitFor(() => expect(screen.getByText('admin')).toBeInTheDocument());
    expect(screen.queryByTestId('new-api-key-token')).not.toBeInTheDocument();
  });

  it('shows revoke confirmation dialog when the revoke icon is clicked', async () => {
    setupFetch([activeKey]);
    const user = userEvent.setup();
    renderWithProviders(<ApiKeys />, {
      appContext: { localeMessages, isPlatformAdmin: true },
    });
    await waitFor(() => expect(screen.getByText('admin')).toBeInTheDocument());
    const revokeButton = screen.getAllByRole('button').find(
      (btn) => btn.querySelector('[data-testid="DeleteIcon"]')
    );
    await user.click(revokeButton);
    await waitFor(() =>
      expect(screen.getByText('Confirm Revocation')).toBeInTheDocument()
    );
  });
});
