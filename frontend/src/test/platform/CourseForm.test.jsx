import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import CourseForm from '../../../platform/courses/components/CourseForm';

vi.mock('../../render.jsx');

const localeMessages = {
  course_title: 'Course Title',
  course_slug: 'Slug',
  slug_tooltip: 'The course slug is used in URLs. You can not edit it later.',
  slug_no_space: 'Slug cannot contain spaces. Use hyphens instead.',
};

const createProps = {
  successCallback: vi.fn(),
  failureCallback: vi.fn(),
  cancelCallback: vi.fn(),
  activeOrganizationId: '1',
  createMode: true,
};

describe('CourseForm slug auto-population', () => {
  it('auto-populates the slug from the title while the slug is untouched (create mode)', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CourseForm {...createProps} />, {
      appContext: { localeMessages },
    });

    await user.type(screen.getByLabelText(/Course Title/), 'My Great Course!');

    expect(screen.getByLabelText(/Slug/)).toHaveValue('my-great-course');
  });

  it('stops auto-syncing once the slug has been edited manually', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CourseForm {...createProps} />, {
      appContext: { localeMessages },
    });

    await user.type(screen.getByLabelText(/Course Title/), 'My Great Course');
    await user.clear(screen.getByLabelText(/Slug/));
    await user.type(screen.getByLabelText(/Slug/), 'custom-slug');
    await user.type(screen.getByLabelText(/Course Title/), ' Extended');

    expect(screen.getByLabelText(/Slug/)).toHaveValue('custom-slug');
  });

  it('does not auto-populate the slug in edit mode', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        title: 'Existing Course',
        slug: 'existing-slug',
        description: 'A description.',
        target_audience: '',
        language: 'en',
        is_public: true,
        send_certificate: true,
        image: null,
        image_path: null,
        imap_connection_id: null,
        newsletter_id: null,
        external_references: [],
        instructors: [],
      }),
    });
    const user = userEvent.setup();
    renderWithProviders(
      <CourseForm {...createProps} createMode={false} courseId="1" />,
      { appContext: { localeMessages } }
    );

    // Edit mode fetches course data on mount and disables the slug field;
    // typing in the title (once loaded) must never populate the slug.
    const titleField = await screen.findByLabelText(/Course Title/);
    await user.type(titleField, ' Updated');

    expect(screen.getByLabelText(/Slug/)).toHaveValue('existing-slug');
  });
});
