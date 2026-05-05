import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import CreateInstructorForm from '../../../platform/courses/components/CreateInstructorForm';

vi.mock('../../render.jsx');

const localeMessages = {
  instructor_email: 'Instructor Email',
  instructor_display_name: 'Display Name',
  instructor_photo: 'Photo',
  add_instructor: 'Add Instructor',
  email_required_helper_text: 'Email is required.',
  invalid_email_helper_text: 'Invalid email address.',
  instructor_display_name_required: 'Display name is required.',
  instructor_add_failed: 'Failed to add instructor.',
  upload_button_label: 'Upload',
  uploaded_image_alt: 'Uploaded image',
  remove_image: 'Remove',
};

describe('CreateInstructorForm', () => {
  it('renders email, display name fields and add button', () => {
    renderWithProviders(
      <CreateInstructorForm onSuccess={vi.fn()} activeOrganizationId="1" />,
      { appContext: { localeMessages } }
    );
    expect(screen.getByLabelText(/Instructor Email/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Display Name/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Add Instructor' })).toBeInTheDocument();
  });

  it('shows email required error when email is missing', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <CreateInstructorForm onSuccess={vi.fn()} activeOrganizationId="1" />,
      { appContext: { localeMessages } }
    );
    await user.click(screen.getByRole('button', { name: 'Add Instructor' }));
    await waitFor(() => {
      expect(screen.getByText('Email is required.')).toBeInTheDocument();
    });
  });

  it('shows invalid email error for bad format', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <CreateInstructorForm onSuccess={vi.fn()} activeOrganizationId="1" />,
      { appContext: { localeMessages } }
    );
    await user.type(screen.getByLabelText(/Instructor Email/), 'not-valid');
    await user.click(screen.getByRole('button', { name: 'Add Instructor' }));
    await waitFor(() => {
      expect(screen.getByText('Invalid email address.')).toBeInTheDocument();
    });
  });

  it('shows display name required error when display name is empty', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <CreateInstructorForm onSuccess={vi.fn()} activeOrganizationId="1" />,
      { appContext: { localeMessages } }
    );
    await user.type(screen.getByLabelText(/Instructor Email/), 'instructor@example.com');
    await user.click(screen.getByRole('button', { name: 'Add Instructor' }));
    await waitFor(() => {
      expect(screen.getByText('Display name is required.')).toBeInTheDocument();
    });
  });

  it('calls onSuccess after successful form submission', async () => {
    const onSuccess = vi.fn();
    global.fetch.mockImplementation((url) => {
      if (url.includes('get-or-create-by-email')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ id: '20' }) });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ id: '30', email: 'instructor@example.com' }),
      });
    });
    const user = userEvent.setup();
    renderWithProviders(
      <CreateInstructorForm onSuccess={onSuccess} activeOrganizationId="1" />,
      { appContext: { localeMessages } }
    );
    await user.type(screen.getByLabelText(/Instructor Email/), 'instructor@example.com');
    await user.type(screen.getByLabelText(/Display Name/), 'Dr. Smith');
    await user.click(screen.getByRole('button', { name: 'Add Instructor' }));
    await waitFor(() => expect(onSuccess).toHaveBeenCalled());
  });
});
