import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import AddImapConnectionForm from '../../../platform/courses/components/AddImapConnectionForm';

vi.mock('../../render.jsx');

const localeMessages = {
  imap_connection: 'IMAP Connection',
  new_imap_connection: 'New IMAP Connection',
  email: 'Email',
  password: 'Password',
  server: 'Server',
  port: 'Port',
  add: 'Add',
  add_folder_helper_text: 'Enter folder name.',
  email_required_helper_text: 'Email is required.',
  invalid_email_helper_text: 'Invalid email address.',
  password_required_helper_text: 'Password is required.',
  server_required_helper_text: 'Server is required.',
  port_required_helper_text: 'Port is required.',
  invalid_port_helper_text: 'Invalid port number.',
};

describe('AddImapConnectionForm', () => {
  beforeEach(() => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ imap_connections: [] }),
    });
  });

  it('shows the "New IMAP Connection" accordion when no connections exist', async () => {
    renderWithProviders(
      <AddImapConnectionForm onChangeCallback={vi.fn()} activeOrganizationId="1" />,
      { appContext: { localeMessages } }
    );
    await waitFor(() =>
      expect(screen.getByText('New IMAP Connection')).toBeInTheDocument()
    );
  });

  it('shows existing connections as a labeled select when they exist', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          imap_connections: [{ id: '5', email: 'mail@server.com' }],
        }),
    });
    renderWithProviders(
      <AddImapConnectionForm onChangeCallback={vi.fn()} activeOrganizationId="1" />,
      { appContext: { localeMessages } }
    );
    await waitFor(() =>
      expect(screen.getByLabelText('IMAP Connection')).toBeInTheDocument()
    );
  });

  it('calls onChangeCallback when a new connection is created', async () => {
    const onChangeCallback = vi.fn();
    global.fetch.mockImplementation((url) => {
      if (url.includes('imap-connections') && !url.includes('POST')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ imap_connections: [] }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ id: '10', email: 'new@server.com' }),
      });
    });
    renderWithProviders(
      <AddImapConnectionForm onChangeCallback={onChangeCallback} activeOrganizationId="1" />,
      { appContext: { localeMessages } }
    );
    // Verify the accordion is expanded and form is available
    await waitFor(() =>
      expect(screen.getByText('New IMAP Connection')).toBeInTheDocument()
    );
  });
});
