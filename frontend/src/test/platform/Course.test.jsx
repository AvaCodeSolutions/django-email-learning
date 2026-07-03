import { describe, it, expect, beforeEach, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import Course from '../../../platform/course/Course';

vi.mock('../../render.jsx');
vi.mock('vite/modulepreload-polyfill', () => ({}));

const localeMessages = {
  course_management: 'Courses',
  course_disabled_banner: 'This course is disabled. Learners cannot be enrolled until you ENABLE_LINK.',
  course_disabled_banner_link: 'enable it',
  enable_course: 'Enable COURSE_NAME',
  course_enable_confirmation: 'Are you sure you want to enable the course COURSE_NAME?',
  cancel: 'Cancel',
  continue: 'Continue',
  server_error: 'Server error occurred. Please try again later.',
  enroll_learner: 'Enroll Learner',
  tab_manage_course_content: 'Manage Course Content',
  total_enrollments: 'Total Enrollments',
};

const baseAppContext = {
  courseId: '5',
  courseTitle: 'Sample Course',
  userRole: 'admin',
  localeMessages,
};

describe('Course', () => {
  beforeEach(() => {
    window.localStorage.setItem('activeOrganizationId', '1');
    global.fetch.mockImplementation((url) => {
      if (url.includes('/contents')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ course_contents: [] }) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  it('does not show the disabled banner when the course is enabled', () => {
    renderWithProviders(<Course />, {
      appContext: { ...baseAppContext, courseEnabled: true },
    });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('does not show the disabled banner when courseEnabled is not provided', () => {
    renderWithProviders(<Course />, { appContext: baseAppContext });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows the disabled banner with a linked "enable it" when the course is disabled', () => {
    renderWithProviders(<Course />, {
      appContext: { ...baseAppContext, courseEnabled: false },
    });
    expect(screen.getByRole('alert')).toHaveTextContent(
      'This course is disabled. Learners cannot be enrolled until you enable it.'
    );
    expect(screen.getByRole('button', { name: 'enable it' })).toBeInTheDocument();
  });

  it('opens the enable confirmation dialog when "enable it" is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Course />, {
      appContext: { ...baseAppContext, courseEnabled: false },
    });
    await user.click(screen.getByRole('button', { name: 'enable it' }));
    expect(await screen.findByText('Enable Sample Course')).toBeInTheDocument();
  });

  it('hides the disabled banner and re-enables the Enroll button after confirming enable', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Course />, {
      appContext: { ...baseAppContext, courseEnabled: false },
    });
    await user.click(screen.getByRole('button', { name: 'enable it' }));
    await user.click(await screen.findByRole('button', { name: 'Continue' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: localeMessages.enroll_learner })).toBeEnabled();
  });

  it('disables the Enroll Learner button when the course is disabled', () => {
    renderWithProviders(<Course />, {
      appContext: { ...baseAppContext, courseEnabled: false },
    });
    expect(screen.getByRole('button', { name: localeMessages.enroll_learner })).toBeDisabled();
  });

  it('keeps the Enroll Learner button enabled when the course is enabled', () => {
    renderWithProviders(<Course />, {
      appContext: { ...baseAppContext, courseEnabled: true },
    });
    expect(screen.getByRole('button', { name: localeMessages.enroll_learner })).toBeEnabled();
  });

  it('hides the enrollment analytics summary when the course is disabled', () => {
    renderWithProviders(<Course />, {
      appContext: { ...baseAppContext, courseEnabled: false },
    });
    expect(screen.queryByText(localeMessages.total_enrollments)).not.toBeInTheDocument();
  });

  it('shows the enrollment analytics summary when the course is enabled', () => {
    renderWithProviders(<Course />, {
      appContext: { ...baseAppContext, courseEnabled: true },
    });
    expect(screen.getByText(localeMessages.total_enrollments)).toBeInTheDocument();
  });
});
