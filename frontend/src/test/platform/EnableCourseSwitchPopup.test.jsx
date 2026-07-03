import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import EnableCourseSwitchPopup from '../../../platform/courses/components/EnableCourseSwitchPopup';

vi.mock('../../render.jsx');

const localeMessages = {
  enable_course: 'Enable COURSE_NAME',
  disable_course: 'Disable COURSE_NAME',
  course_enable_confirmation: 'Do you want to enable COURSE_NAME?',
  course_disable_confirmation: 'Do you want to disable COURSE_NAME?',
  cancel: 'Cancel',
  continue: 'Continue',
  server_error: 'Server error occurred. Please try again later.',
};

describe('EnableCourseSwitchPopup', () => {
  beforeEach(() => {
    window.localStorage.setItem('activeOrganizationId', '1');
  });

  it('renders the enable title with the course name', () => {
    renderWithProviders(
      <EnableCourseSwitchPopup
        courseId="3"
        action="enable"
        courseTitle="React Course"
        handleClose={vi.fn()}
        handleSuccess={vi.fn()}
      />,
      { appContext: { localeMessages } }
    );
    expect(screen.getByText('Enable React Course')).toBeInTheDocument();
  });

  it('renders the disable title with the course name', () => {
    renderWithProviders(
      <EnableCourseSwitchPopup
        courseId="3"
        action="disable"
        courseTitle="React Course"
        handleClose={vi.fn()}
        handleSuccess={vi.fn()}
      />,
      { appContext: { localeMessages } }
    );
    expect(screen.getByText('Disable React Course')).toBeInTheDocument();
  });

  it('calls handleClose when cancel button is clicked', async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();
    renderWithProviders(
      <EnableCourseSwitchPopup
        courseId="3"
        action="enable"
        courseTitle="React Course"
        handleClose={handleClose}
        handleSuccess={vi.fn()}
      />,
      { appContext: { localeMessages } }
    );
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(handleClose).toHaveBeenCalled();
  });

  it('calls handleSuccess and handleClose after confirming', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: '3', enabled: true }),
    });
    const user = userEvent.setup();
    const handleSuccess = vi.fn();
    const handleClose = vi.fn();
    renderWithProviders(
      <EnableCourseSwitchPopup
        courseId="3"
        action="enable"
        courseTitle="React Course"
        handleClose={handleClose}
        handleSuccess={handleSuccess}
      />,
      { appContext: { localeMessages } }
    );
    await user.click(screen.getByRole('button', { name: 'Continue' }));
    await waitFor(() => expect(handleSuccess).toHaveBeenCalledWith({ id: '3', enabled: true }));
    expect(handleClose).toHaveBeenCalled();
  });

  it('shows the error message from the API response when the request fails', async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 409,
      json: () => Promise.resolve({ error: 'Cannot enable a course that has no content.' }),
    });
    const user = userEvent.setup();
    const handleClose = vi.fn();
    renderWithProviders(
      <EnableCourseSwitchPopup
        courseId="3"
        action="enable"
        courseTitle="React Course"
        handleClose={handleClose}
        handleSuccess={vi.fn()}
      />,
      { appContext: { localeMessages } }
    );
    await user.click(screen.getByRole('button', { name: 'Continue' }));
    await waitFor(() =>
      expect(screen.getByText('Cannot enable a course that has no content.')).toBeInTheDocument()
    );
    expect(handleClose).not.toHaveBeenCalled();
  });

  it('shows a generic error message when the API response has no error field', async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({}),
    });
    const user = userEvent.setup();
    renderWithProviders(
      <EnableCourseSwitchPopup
        courseId="3"
        action="enable"
        courseTitle="React Course"
        handleClose={vi.fn()}
        handleSuccess={vi.fn()}
      />,
      { appContext: { localeMessages } }
    );
    await user.click(screen.getByRole('button', { name: 'Continue' }));
    await waitFor(() =>
      expect(screen.getByText('Server error occurred. Please try again later.')).toBeInTheDocument()
    );
  });
});
