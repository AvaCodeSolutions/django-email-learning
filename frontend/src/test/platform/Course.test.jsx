import { describe, it, expect, beforeEach, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import Course from '../../../platform/course/Course';

vi.mock('../../render.jsx');
vi.mock('vite/modulepreload-polyfill', () => ({}));

const localeMessages = {
  course_management: 'Courses',
  course_disabled_banner: 'This course is disabled. Learners cannot be enrolled until you enable it.',
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
  });

  it('does not show the disabled banner when the course is enabled', () => {
    renderWithProviders(<Course />, {
      appContext: { ...baseAppContext, courseEnabled: true },
    });
    expect(screen.queryByText(localeMessages.course_disabled_banner)).not.toBeInTheDocument();
  });

  it('does not show the disabled banner when courseEnabled is not provided', () => {
    renderWithProviders(<Course />, { appContext: baseAppContext });
    expect(screen.queryByText(localeMessages.course_disabled_banner)).not.toBeInTheDocument();
  });

  it('shows the disabled banner when the course is disabled', () => {
    renderWithProviders(<Course />, {
      appContext: { ...baseAppContext, courseEnabled: false },
    });
    expect(screen.getByText(localeMessages.course_disabled_banner)).toBeInTheDocument();
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
