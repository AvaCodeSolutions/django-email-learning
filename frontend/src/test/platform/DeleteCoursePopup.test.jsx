import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import DeleteCoursePopup from '../../../platform/courses/components/DeleteCoursePopup';

vi.mock('../../render.jsx');

const localeMessages = {
  delete_course: 'Delete COURSE_NAME',
  course_delete_confirmation: 'Are you sure you want to delete COURSE_NAME?',
  cancel: 'Cancel',
  delete: 'Delete',
};

const defaultProps = {
  courseId: '7',
  courseTitle: 'Python Basics',
  handleClose: vi.fn(),
  handleSuccess: vi.fn(),
};

describe('DeleteCoursePopup', () => {
  beforeEach(() => {
    window.localStorage.setItem('activeOrganizationId', '1');
    defaultProps.handleClose.mockClear();
    defaultProps.handleSuccess.mockClear();
  });

  it('renders the title with the course name', () => {
    renderWithProviders(<DeleteCoursePopup {...defaultProps} />, {
      appContext: { localeMessages },
    });
    expect(screen.getByText('Delete Python Basics')).toBeInTheDocument();
  });

  it('renders the confirmation message', () => {
    renderWithProviders(<DeleteCoursePopup {...defaultProps} />, {
      appContext: { localeMessages },
    });
    expect(
      screen.getByText('Are you sure you want to delete Python Basics?')
    ).toBeInTheDocument();
  });

  it('calls handleClose when cancel is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<DeleteCoursePopup {...defaultProps} />, {
      appContext: { localeMessages },
    });
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(defaultProps.handleClose).toHaveBeenCalled();
  });

  it('calls handleSuccess and handleClose after successful deletion', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });
    const user = userEvent.setup();
    renderWithProviders(<DeleteCoursePopup {...defaultProps} />, {
      appContext: { localeMessages },
    });
    await user.click(screen.getByRole('button', { name: 'Delete' }));
    await waitFor(() => expect(defaultProps.handleSuccess).toHaveBeenCalled());
    expect(defaultProps.handleClose).toHaveBeenCalled();
  });
});
