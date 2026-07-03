import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import EnrollMenu from '../../../platform/course/components/EnrollMenu';

vi.mock('../../render.jsx');

const localeMessages = {
  enroll_learner: 'Enroll Learner',
  manual_email: 'Manual Email',
  from_google_workspace: 'From Google Workspace',
  email: 'Email',
  cancel: 'Cancel',
  enroll: 'Enroll',
  email_required: 'Email is required.',
  enrollment_failed: 'Enrollment failed.',
  enrollment_success: 'Learner enrolled successfully.',
  google_workspace_description: 'Import learners from Google Workspace.',
  authorize_description: 'Authorize access to your Google account.',
  authorize_button: 'Authorize with Google',
};

describe('EnrollMenu', () => {
  beforeEach(() => {
    window.localStorage.setItem('activeOrganizationId', '1');
  });

  it('renders the Enroll Learner button', () => {
    renderWithProviders(<EnrollMenu successCallback={vi.fn()} />, {
      appContext: { localeMessages, courseId: '5', userRole: 'admin' },
    });
    expect(screen.getByRole('button', { name: /Enroll Learner/ })).toBeInTheDocument();
  });

  it('opens the dropdown menu when button is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<EnrollMenu successCallback={vi.fn()} />, {
      appContext: { localeMessages, courseId: '5', userRole: 'admin' },
    });
    await user.click(screen.getByRole('button', { name: /Enroll Learner/ }));
    expect(screen.getByText('Manual Email')).toBeInTheDocument();
  });

  it('opens the manual enrollment dialog when "Manual Email" is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<EnrollMenu successCallback={vi.fn()} />, {
      appContext: { localeMessages, courseId: '5', userRole: 'admin' },
    });
    await user.click(screen.getByRole('button', { name: /Enroll Learner/ }));
    await user.click(screen.getByText('Manual Email'));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Enroll' })).toBeInTheDocument();
  });

  it('shows email required error when submitting manual enrollment without email', async () => {
    const user = userEvent.setup();
    renderWithProviders(<EnrollMenu successCallback={vi.fn()} />, {
      appContext: { localeMessages, courseId: '5', userRole: 'admin' },
    });
    await user.click(screen.getByRole('button', { name: /Enroll Learner/ }));
    await user.click(screen.getByText('Manual Email'));
    await user.click(screen.getByRole('button', { name: 'Enroll' }));
    await waitFor(() =>
      expect(screen.getByText('Email is required.')).toBeInTheDocument()
    );
  });

  it('disables the Enroll Learner button when the course is disabled', () => {
    renderWithProviders(<EnrollMenu successCallback={vi.fn()} />, {
      appContext: { localeMessages, courseId: '5', userRole: 'admin', courseEnabled: false },
    });
    expect(screen.getByRole('button', { name: /Enroll Learner/ })).toBeDisabled();
  });

  it('keeps the Enroll Learner button enabled when courseEnabled is not specified', () => {
    renderWithProviders(<EnrollMenu successCallback={vi.fn()} />, {
      appContext: { localeMessages, courseId: '5', userRole: 'admin' },
    });
    expect(screen.getByRole('button', { name: /Enroll Learner/ })).toBeEnabled();
  });

  it('calls successCallback after successful manual enrollment', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: '99' }),
    });
    const successCallback = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<EnrollMenu successCallback={successCallback} />, {
      appContext: { localeMessages, courseId: '5', userRole: 'admin' },
    });
    await user.click(screen.getByRole('button', { name: /Enroll Learner/ }));
    await user.click(screen.getByText('Manual Email'));
    await user.type(screen.getByLabelText(/Email/), 'learner@example.com');
    await user.click(screen.getByRole('button', { name: 'Enroll' }));
    await waitFor(() => expect(successCallback).toHaveBeenCalled());
  });
});
