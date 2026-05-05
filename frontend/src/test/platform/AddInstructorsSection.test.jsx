import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import AddInstructorsSection from '../../../platform/courses/components/AddInstructorsSection';

vi.mock('../../render.jsx');

const localeMessages = {
  select_instructors: 'Select Instructors',
  new_instructor: 'New Instructor',
  instructor_email: 'Instructor Email',
  instructor_display_name: 'Display Name',
  instructor_photo: 'Photo',
  add_instructor: 'Add Instructor',
  email_required_helper_text: 'Email is required.',
  invalid_email_helper_text: 'Invalid email.',
  instructor_display_name_required: 'Display name is required.',
  instructor_add_failed: 'Failed to add instructor.',
  upload_button_label: 'Upload',
  uploaded_image_alt: 'Uploaded image',
  remove_image: 'Remove',
};

describe('AddInstructorsSection', () => {
  beforeEach(() => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ organization_users: [] }),
    });
  });

  it('shows the "New Instructor" accordion when no instructors exist', async () => {
    renderWithProviders(
      <AddInstructorsSection onChangeCallback={vi.fn()} activeOrganizationId="1" />,
      { appContext: { localeMessages } }
    );
    await waitFor(() =>
      expect(screen.getByText('New Instructor')).toBeInTheDocument()
    );
  });

  it('shows instructor select dropdown when instructors exist', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          organization_users: [
            { id: '3', email: 'prof@example.com', display_name: 'Prof. Jones', can_act_as_instructor: true },
          ],
        }),
    });
    renderWithProviders(
      <AddInstructorsSection onChangeCallback={vi.fn()} activeOrganizationId="1" />,
      { appContext: { localeMessages } }
    );
    await waitFor(() =>
      expect(screen.getByLabelText('Select Instructors')).toBeInTheDocument()
    );
  });

  it('pre-selects initial instructor IDs', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          organization_users: [
            { id: '3', email: 'prof@example.com', display_name: 'Prof. Jones', can_act_as_instructor: true },
          ],
        }),
    });
    renderWithProviders(
      <AddInstructorsSection
        onChangeCallback={vi.fn()}
        activeOrganizationId="1"
        initialInstructorIds={['3']}
      />,
      { appContext: { localeMessages } }
    );
    await waitFor(() =>
      expect(screen.getAllByText('Prof. Jones').length).toBeGreaterThan(0)
    );
  });
});
