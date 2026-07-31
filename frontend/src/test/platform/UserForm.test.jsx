import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import UserForm from '../../../platform/organization/components/UserForm';

vi.mock('../../render.jsx');

const localeMessages = {
  email: 'Email',
  display_name: 'Display Name',
  role: 'Role',
  viewer: 'Viewer',
  editor: 'Editor',
  instructor: 'Instructor',
  admin: 'Admin',
  add_users_to_organization: 'Add Users to Organization',
  change_user_role: 'Change User Role',
  add_user: 'Add User',
  edit_user: 'Edit User',
  photo: 'Photo',
  viewer_role_description: 'Can view content.',
  editor_role_description: 'Can edit content.',
  instructor_role_description: 'Can instruct learners.',
  admin_role_description: 'Has full access.',
  display_name_required: 'Display name is required for instructors.',
  failed_to_add_user: 'Failed to add user.',
  failed_to_get_or_create_user: 'Failed to get or create user.',
  failed_to_update_user_role: 'Failed to update user role.',
  upload_button_label: 'Upload',
  uploaded_image_alt: 'Uploaded image',
  remove_image: 'Remove',
};

describe('UserForm', () => {
  it('shows "Add Users to Organization" heading when no user is provided', () => {
    renderWithProviders(
      <UserForm onClose={vi.fn()} organizationId="1" refreshUsers={vi.fn()} />,
      { appContext: { localeMessages } }
    );
    expect(screen.getByText('Add Users to Organization')).toBeInTheDocument();
  });

  it('shows "Change User Role" heading when editing an existing user', () => {
    const user = { email: 'bob@example.com', role: 'viewer', display_name: 'Bob', user_id: '5' };
    renderWithProviders(
      <UserForm onClose={vi.fn()} organizationId="1" refreshUsers={vi.fn()} user={user} />,
      { appContext: { localeMessages } }
    );
    expect(screen.getByText('Change User Role')).toBeInTheDocument();
  });

  it('pre-fills email when editing an existing user', () => {
    const user = { email: 'carol@example.com', role: 'editor', display_name: '', user_id: '6' };
    renderWithProviders(
      <UserForm onClose={vi.fn()} organizationId="1" refreshUsers={vi.fn()} user={user} />,
      { appContext: { localeMessages } }
    );
    expect(screen.getByDisplayValue('carol@example.com')).toBeInTheDocument();
  });

  it('shows display name error when role is instructor and display name is missing', async () => {
    const user = userEvent.setup();
    // Create an edit-mode user with instructor role and no display name
    const instructorUser = {
      email: 'instructor@example.com',
      role: 'instructor',
      display_name: '',
      user_id: '8',
    };
    renderWithProviders(
      <UserForm
        onClose={vi.fn()}
        organizationId="1"
        refreshUsers={vi.fn()}
        user={instructorUser}
      />,
      { appContext: { localeMessages } }
    );
    // Type whitespace — passes HTML required validation but fails trim() check
    await user.type(screen.getByLabelText(/Display Name/), '   ');
    await user.click(screen.getByRole('button', { name: 'Edit User' }));
    await waitFor(() => {
      expect(
        screen.getByText('Display name is required for instructors.')
      ).toBeInTheDocument();
    });
  });

  it('shows viewer role description', async () => {
    renderWithProviders(
      <UserForm onClose={vi.fn()} organizationId="1" refreshUsers={vi.fn()} />,
      { appContext: { localeMessages } }
    );
    // Default role is viewer, description should be shown
    expect(screen.getByText('Can view content.')).toBeInTheDocument();
  });
});
