import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import Organizations from '../../../platform/organizations/Organizations';

vi.mock('../../render.jsx');

vi.mock('@mui/material', async () => ({
  ...(await vi.importActual('@mui/material')),
  useMediaQuery: vi.fn(() => true),
}));

const localeMessages = {
  organizations: 'Organizations',
  add_organization: 'Add Organization',
  name: 'Name',
  actions: 'Actions',
  private: 'Private',
  confirm_deletion: 'Confirm Deletion',
  are_you_sure_delete_org: 'Are you sure you want to delete ORGANIZATION_NAME?',
  cancel: 'Cancel',
  delete: 'Delete',
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

function setupFetch(organizations = []) {
  global.fetch.mockImplementation((url) => {
    if (url.includes('/status/jobs/')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ jobs: { deliver_contents: null } }),
      });
    }
    if (url.includes('/organizations/')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ organizations }),
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
  });
}

describe('Organizations', () => {
  beforeEach(() => {
    setupFetch();
  });

  it('shows Add Organization button for platform admin', async () => {
    renderWithProviders(<Organizations />, {
      appContext: { localeMessages, isPlatformAdmin: true },
    });
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Add Organization/ })).toBeInTheDocument()
    );
  });

  it('does not show Add Organization button for non-admin', async () => {
    renderWithProviders(<Organizations />, {
      appContext: { localeMessages, isPlatformAdmin: false },
    });
    await waitFor(() =>
      expect(
        screen.queryByRole('button', { name: /Add Organization/ })
      ).not.toBeInTheDocument()
    );
  });

  it('renders organization rows after fetch', async () => {
    setupFetch([{ id: '1', name: 'Acme Corp', is_public: true, public_url: 'https://acme.com' }]);
    renderWithProviders(<Organizations />, {
      appContext: { localeMessages, isPlatformAdmin: true },
    });
    await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument());
  });

  it('shows the delete confirmation dialog when delete is clicked', async () => {
    setupFetch([{ id: '1', name: 'Acme Corp', is_public: false }]);
    const user = userEvent.setup();
    renderWithProviders(<Organizations />, {
      appContext: { localeMessages, isPlatformAdmin: true },
    });
    await waitFor(() => expect(screen.getByText('Acme Corp')).toBeInTheDocument());
    // All icon buttons in the table: public, edit, delete
    const buttons = screen.getAllByRole('button');
    const deleteButton = buttons[buttons.length - 1]; // delete is last
    await user.click(deleteButton);
    await waitFor(() =>
      expect(screen.getByText('Confirm Deletion')).toBeInTheDocument()
    );
  });
});
