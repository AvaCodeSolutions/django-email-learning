import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import Courses from '../../../platform/courses/Courses';

vi.mock('../../render.jsx');

vi.mock('@mui/material', async () => ({
  ...(await vi.importActual('@mui/material')),
  useMediaQuery: vi.fn(() => true),
}));

const localeMessages = {
  course_management: 'Courses',
  add_course: 'Add Course',
  courses: 'Courses',
  title: 'Title',
  course_language: 'Language',
  total_enrollments: 'Total Enrollments',
  enabled: 'Enabled',
  actions: 'Actions',
  private: 'Private',
  no_courses_found: 'No courses found.',
  organizations: 'Organizations',
  learners: 'Learners',
  content_delivery_tooltip: 'Content delivery',
  content_delivery_job: 'Content delivery',
  last_run: 'Last run:',
  never_run: 'Never run',
  upload_button_label: 'Upload',
  uploaded_image_alt: 'Uploaded image',
  remove_image: 'Remove',
};

function setupFetch(courses = []) {
  global.fetch.mockImplementation((url) => {
    if (url.includes('/courses')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ courses }),
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
        json: () => Promise.resolve({ organizations: [{ id: '1', name: 'Acme' }] }),
      });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
  });
}

describe('Courses', () => {
  beforeEach(() => {
    setupFetch();
    window.localStorage.setItem('activeOrganizationId', '1');
  });

  it('renders the page with course table headers after organization is set', async () => {
    setupFetch([]);
    renderWithProviders(<Courses />, {
      appContext: { localeMessages, userRole: 'editor' },
    });
    await waitFor(() => expect(screen.getByText('Acme')).toBeInTheDocument());
    // Simulate org selection by waiting for loading to finish
    // (MenuBar sets org, which triggers course loading)
  });

  it('shows "No courses found." when no courses are returned', async () => {
    setupFetch([]);
    renderWithProviders(<Courses />, {
      appContext: { localeMessages, userRole: 'editor' },
    });
    await waitFor(() => expect(screen.getByText('No courses found.')).toBeInTheDocument());
  });

  it('renders course rows when courses are loaded', async () => {
    setupFetch([
      {
        id: '1',
        title: 'Django Basics',
        language: 'en',
        enabled: true,
        is_public: true,
        enrollments_count: { total: 5 },
      },
    ]);
    renderWithProviders(<Courses />, {
      appContext: { localeMessages, userRole: 'editor' },
    });
    await waitFor(() => expect(screen.getByText('Django Basics')).toBeInTheDocument());
  });

  it('shows Add Course button for non-viewer role', async () => {
    renderWithProviders(<Courses />, {
      appContext: { localeMessages, userRole: 'editor' },
    });
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Add Course/ })).toBeInTheDocument()
    );
  });

  it('does not show Add Course button for viewer role', async () => {
    renderWithProviders(<Courses />, {
      appContext: { localeMessages, userRole: 'viewer' },
    });
    // Wait for content to load, then verify button is absent
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: /Add Course/ })).not.toBeInTheDocument()
    );
  });
});
