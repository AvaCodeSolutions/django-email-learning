import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import DeleteUserDialog from '../../../platform/organization/components/DeleteUserDialog';

vi.mock('../../render.jsx');

const localeMessages = {
  delete_user_with_email: 'Delete USER_EMAIL',
  user_delete_confirmation: 'Are you sure you want to remove USER_EMAIL?',
  delete_note: 'Note: this action cannot be undone.',
  cancel: 'Cancel',
  delete: 'Delete',
};

const testUser = {
  id: '99',
  email: 'alice@example.com',
  organization_id: '5',
};

describe('DeleteUserDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the dialog title with the user email', () => {
    renderWithProviders(
      <DeleteUserDialog user={testUser} handleClose={vi.fn()} handleSuccess={vi.fn()} />,
      { appContext: { localeMessages } }
    );
    expect(screen.getByText('Delete alice@example.com')).toBeInTheDocument();
  });

  it('renders the confirmation text', () => {
    renderWithProviders(
      <DeleteUserDialog user={testUser} handleClose={vi.fn()} handleSuccess={vi.fn()} />,
      { appContext: { localeMessages } }
    );
    expect(
      screen.getByText('Are you sure you want to remove alice@example.com?')
    ).toBeInTheDocument();
  });

  it('calls handleClose when cancel is clicked', async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();
    renderWithProviders(
      <DeleteUserDialog user={testUser} handleClose={handleClose} handleSuccess={vi.fn()} />,
      { appContext: { localeMessages } }
    );
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(handleClose).toHaveBeenCalled();
  });

  it('calls handleSuccess after successful deletion', async () => {
    global.fetch.mockResolvedValue({
      status: 200,
      json: () => Promise.resolve({}),
    });
    const user = userEvent.setup();
    const handleSuccess = vi.fn();
    renderWithProviders(
      <DeleteUserDialog user={testUser} handleClose={vi.fn()} handleSuccess={handleSuccess} />,
      { appContext: { localeMessages } }
    );
    await user.click(screen.getByRole('button', { name: 'Delete' }));
    await waitFor(() => expect(handleSuccess).toHaveBeenCalled());
  });
});
