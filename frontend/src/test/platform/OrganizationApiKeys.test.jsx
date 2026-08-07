import { describe, it, expect, beforeEach, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import Organization from '../../../platform/organization/Organization';

vi.mock('../../render.jsx');

const localeMessages = {
  organizations: 'Organizations',
  general_info: 'General Info',
  members: 'Members',
  actions: 'Actions',
  cancel: 'Cancel',
  api_keys: 'API Keys',
  api_keys_intro: 'API keys let your own systems act on this organization.',
  no_api_keys: 'No API keys yet.',
  create_api_key: 'Create API Key',
  api_key_name: 'Name',
  api_key_name_required: 'Name is required.',
  api_key_scopes: 'Scopes',
  api_key_scopes_required: 'Select at least one scope.',
  api_key_expires_at: 'Expires on',
  api_key_expires_at_helper_text: 'Optional.',
  api_key_create_error: 'Failed to create the API key.',
  key_id: 'Key ID',
  status: 'Status',
  active: 'Active',
  revoked: 'Revoked',
  expired: 'Expired',
  last_used: 'Last Used',
  never_used: 'Never used',
  created_by: 'Created By',
  created_at: 'Created At',
  revoke: 'Revoke',
  confirm_revocation: 'Confirm Revocation',
  are_you_sure_revoke_key: 'Are you sure you want to revoke API_KEY_NAME?',
  copy: 'Copy',
  copied: 'Copied',
  done: 'Done',
  new_api_key_created: 'New API key created',
  copy_key_now_warning: 'Copy this key now. It cannot be shown again.',
};

const organization = {
  id: 1,
  name: 'Acme Corp',
  description: 'A great company.',
  logo: null,
  logo_path: null,
  social_links: [],
  is_public: false,
  public_url: null,
};

const activeKey = {
  id: 7,
  key_id: 'a1b2c3d4e5f60718293a4b5c',
  name: 'Partner integration',
  key_type: 'organization',
  organization_id: 1,
  scopes: ['enrollments:create'],
  created_by: 'orgadmin',
  created_at: '2026-08-07',
  expires_at: null,
  revoked_at: null,
  last_used_at: null,
};

const baseAppContext = {
  organizationId: '1',
  localeMessages,
  isOrganizationAdmin: true,
  availableFeatures: ['organization_api'],
  apiKeyScopes: [{ value: 'enrollments:create', label: 'Create enrollments' }],
};

function setupFetch({ apiKeys = [], onPost } = {}) {
  global.fetch.mockImplementation((url, options) => {
    if (url.includes('/api-keys/') && options?.method === 'POST') {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(onPost(JSON.parse(options.body))) });
    }
    if (url.includes('/api-keys/') && options?.method === 'DELETE') {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ message: 'API Key revoked successfully' }) });
    }
    if (url.includes('/api-keys/')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ api_keys: apiKeys }) });
    }
    if (url.includes('/users/')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ organization_users: [] }) });
    }
    if (url.endsWith('/organizations/1/')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(organization) });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
  });
}

const openApiKeysTab = async (user) => {
  await user.click(await screen.findByRole('tab', { name: /API Keys/i }));
};

describe('Organization API keys tab', () => {
  beforeEach(() => {
    setupFetch();
  });

  it('shows the tab for an organization admin', async () => {
    renderWithProviders(<Organization />, { appContext: baseAppContext });
    expect(await screen.findByRole('tab', { name: /API Keys/i })).toBeInTheDocument();
  });

  it('hides the tab from a non-admin', async () => {
    renderWithProviders(<Organization />, {
      appContext: { ...baseAppContext, isOrganizationAdmin: false, isPlatformAdmin: false },
    });
    await screen.findByRole('tab', { name: /Members/i });
    expect(screen.queryByRole('tab', { name: /API Keys/i })).not.toBeInTheDocument();
  });

  it('hides the tab when the organization_api feature is not available', async () => {
    renderWithProviders(<Organization />, {
      appContext: { ...baseAppContext, availableFeatures: [] },
    });
    await screen.findByRole('tab', { name: /Members/i });
    expect(screen.queryByRole('tab', { name: /API Keys/i })).not.toBeInTheDocument();
  });

  it('does not fetch keys when the feature is unavailable', async () => {
    renderWithProviders(<Organization />, {
      appContext: { ...baseAppContext, availableFeatures: [] },
    });
    await screen.findByRole('tab', { name: /Members/i });

    const requestedUrls = global.fetch.mock.calls.map(([url]) => url);
    expect(requestedUrls.some(url => url.includes('/api-keys/'))).toBe(false);
  });

  it('shows the shared empty-table state when there are no keys', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Organization />, { appContext: baseAppContext });
    await openApiKeysTab(user);

    expect(await screen.findByText('No API keys yet.')).toBeInTheDocument();
    // EmptyTableState renders inside the table, so the headers stay visible
    // and the message carries the shared inbox icon — this is what
    // distinguishes it from a bare <Typography> fallback.
    expect(screen.getByTestId('InboxIcon')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Key ID' })).toBeInTheDocument();
  });

  it('lists a key with its scopes and metadata', async () => {
    setupFetch({ apiKeys: [activeKey] });
    const user = userEvent.setup();
    renderWithProviders(<Organization />, { appContext: baseAppContext });
    await openApiKeysTab(user);

    expect(await screen.findByText('Partner integration')).toBeInTheDocument();
    expect(screen.getByText('a1b2c3d4e5f60718293a4b5c')).toBeInTheDocument();
    expect(screen.getByText('enrollments:create')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('orgadmin')).toBeInTheDocument();
    expect(screen.getByText('Never used')).toBeInTheDocument();
  });

  it('never renders a token in the listing', async () => {
    setupFetch({ apiKeys: [activeKey] });
    const user = userEvent.setup();
    renderWithProviders(<Organization />, { appContext: baseAppContext });
    await openApiKeysTab(user);
    await screen.findByText('Partner integration');

    expect(screen.queryByTestId('new-api-key-token')).not.toBeInTheDocument();
  });

  it('marks a revoked key and offers no revoke action', async () => {
    setupFetch({ apiKeys: [{ ...activeKey, revoked_at: '2026-08-08' }] });
    const user = userEvent.setup();
    renderWithProviders(<Organization />, { appContext: baseAppContext });
    await openApiKeysTab(user);

    expect(await screen.findByText('Revoked')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Revoke Partner integration/ })).not.toBeInTheDocument();
  });

  it('marks a key past its expiry as expired', async () => {
    setupFetch({ apiKeys: [{ ...activeKey, expires_at: '2020-01-01T00:00:00Z' }] });
    const user = userEvent.setup();
    renderWithProviders(<Organization />, { appContext: baseAppContext });
    await openApiKeysTab(user);

    expect(await screen.findByText('Expired')).toBeInTheDocument();
  });

  it('creates a key and shows the token once', async () => {
    const posted = [];
    setupFetch({
      onPost: (body) => {
        posted.push(body);
        return { ...activeKey, token: 'elk_a1b2c3d4e5f60718293a4b5c_supersecret' };
      },
    });
    const user = userEvent.setup();
    renderWithProviders(<Organization />, { appContext: baseAppContext });
    await openApiKeysTab(user);

    await user.click(await screen.findByRole('button', { name: 'Create API Key' }));
    await user.type(await screen.findByLabelText(/Name/), 'Partner integration');
    await user.click(screen.getByRole('checkbox', { name: /Create enrollments/ }));
    await user.click(screen.getByRole('button', { name: 'Create API Key' }));

    expect(await screen.findByText('New API key created')).toBeInTheDocument();
    expect(screen.getByTestId('new-api-key-token')).toHaveTextContent('elk_a1b2c3d4e5f60718293a4b5c_supersecret');
    expect(screen.getByText('Copy this key now. It cannot be shown again.')).toBeInTheDocument();

    expect(posted).toEqual([{ name: 'Partner integration', scopes: ['enrollments:create'] }]);
  });

  it('refuses to submit without a scope', async () => {
    const posted = [];
    setupFetch({ onPost: (body) => { posted.push(body); return activeKey; } });
    const user = userEvent.setup();
    renderWithProviders(<Organization />, { appContext: baseAppContext });
    await openApiKeysTab(user);

    await user.click(await screen.findByRole('button', { name: 'Create API Key' }));
    await user.type(await screen.findByLabelText(/Name/), 'No scopes');
    await user.click(screen.getByRole('button', { name: 'Create API Key' }));

    expect(await screen.findByText('Select at least one scope.')).toBeInTheDocument();
    expect(posted).toEqual([]);
  });

  it('requires a name', async () => {
    const posted = [];
    setupFetch({ onPost: (body) => { posted.push(body); return activeKey; } });
    const user = userEvent.setup();
    renderWithProviders(<Organization />, { appContext: baseAppContext });
    await openApiKeysTab(user);

    await user.click(await screen.findByRole('button', { name: 'Create API Key' }));
    await user.click(await screen.findByRole('checkbox', { name: /Create enrollments/ }));
    await user.click(screen.getByRole('button', { name: 'Create API Key' }));

    expect(await screen.findByText('Name is required.')).toBeInTheDocument();
    expect(posted).toEqual([]);
  });

  it('sends an expiry as a datetime when one is chosen', async () => {
    const posted = [];
    setupFetch({ onPost: (body) => { posted.push(body); return { ...activeKey, token: 'elk_x_y' }; } });
    const user = userEvent.setup();
    renderWithProviders(<Organization />, { appContext: baseAppContext });
    await openApiKeysTab(user);

    await user.click(await screen.findByRole('button', { name: 'Create API Key' }));
    await user.type(await screen.findByLabelText(/Name/), 'Expiring key');
    await user.click(screen.getByRole('checkbox', { name: /Create enrollments/ }));
    await user.type(screen.getByLabelText(/Expires on/), '2027-01-01');
    await user.click(screen.getByRole('button', { name: 'Create API Key' }));

    await waitFor(() => expect(posted).toHaveLength(1));
    expect(posted[0].expires_at).toBe('2027-01-01T00:00:00Z');
  });

  it('confirms before revoking', async () => {
    setupFetch({ apiKeys: [activeKey] });
    const user = userEvent.setup();
    renderWithProviders(<Organization />, { appContext: baseAppContext });
    await openApiKeysTab(user);

    await user.click(await screen.findByRole('button', { name: /Revoke Partner integration/ }));

    expect(await screen.findByText('Confirm Revocation')).toBeInTheDocument();
    expect(screen.getByText('Are you sure you want to revoke Partner integration?')).toBeInTheDocument();
  });
});
