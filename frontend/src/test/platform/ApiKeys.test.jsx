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

const localeMessages = {
  api_keys: 'API Keys',
  api_key_intro: 'Use API keys to access the API.',
  add_api_key: 'Add API Key',
  key: 'Key',
  created_by: 'Created By',
  created_at: 'Created At',
  actions: 'Actions',
  copy: 'Copy',
  confirm_deletion: 'Confirm Deletion',
  are_you_sure_delete_key: 'Are you sure you want to delete this API key?',
  cancel: 'Cancel',
  delete: 'Delete',
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

  it('shows the key table after loading keys', async () => {
    setupFetch([
      { id: '1', key: 'abc123', created_by: 'admin', created_at: '2024-01-01', visible: false },
    ]);
    renderWithProviders(<ApiKeys />, {
      appContext: { localeMessages, isPlatformAdmin: true },
    });
    await waitFor(() => expect(screen.getByText('admin')).toBeInTheDocument());
    expect(screen.getByText('2024-01-01')).toBeInTheDocument();
  });

  it('adds a new API key when Add API Key is clicked', async () => {
    const user = userEvent.setup();
    global.fetch.mockImplementation((url, options) => {
      if (url.includes('/api_keys/') && options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            id: '2', key: 'new-key-xyz', created_by: 'admin', created_at: '2024-06-01', visible: false,
          }),
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
    await waitFor(() => expect(screen.getByText('2024-06-01')).toBeInTheDocument());
  });

  it('shows delete confirmation dialog when delete icon is clicked', async () => {
    setupFetch([
      { id: '1', key: 'abc123', created_by: 'admin', created_at: '2024-01-01', visible: false },
    ]);
    const user = userEvent.setup();
    renderWithProviders(<ApiKeys />, {
      appContext: { localeMessages, isPlatformAdmin: true },
    });
    await waitFor(() => expect(screen.getByText('admin')).toBeInTheDocument());
    // Find the button containing the DeleteIcon svg
    const deleteButton = screen.getAllByRole('button').find(
      (btn) => btn.querySelector('[data-testid="DeleteIcon"]')
    );
    await user.click(deleteButton);
    await waitFor(() =>
      expect(screen.getByText('Confirm Deletion')).toBeInTheDocument()
    );
  });
});
