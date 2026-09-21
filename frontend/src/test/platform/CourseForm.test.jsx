import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import CourseForm from '../../../platform/courses/components/CourseForm';

vi.mock('../../render.jsx');

const localeMessages = {
  course_title: 'Course Title',
  course_slug: 'Slug',
  slug_tooltip: 'The course slug is used in URLs. You can not edit it later.',
  slug_no_space: 'Slug cannot contain spaces. Use hyphens instead.',
  imap_connection_tooltip: 'Connect an inbox so learners can interact with this course by email.',
  description_char_limit_helper_text: 'COUNT/1000 characters used.',
  description_max_length_helper_text: 'The course description must be 1000 characters or fewer.',
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

  it('shows the slug tooltip as helper text on focus in mobile view, and hides it on blur', async () => {
    const matchMediaSpy = vi.spyOn(window, 'matchMedia').mockImplementation((query) => ({
      matches: true,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    const user = userEvent.setup();
    renderWithProviders(<CourseForm {...createProps} />, {
      appContext: { localeMessages },
    });

    const slugField = screen.getByLabelText(/Slug/);
    expect(screen.queryByText(localeMessages.slug_tooltip)).not.toBeInTheDocument();

    await user.click(slugField);
    expect(screen.getByText(localeMessages.slug_tooltip)).toBeInTheDocument();

    await user.tab();
    expect(screen.queryByText(localeMessages.slug_tooltip)).not.toBeInTheDocument();

    matchMediaSpy.mockRestore();
  });

  it('opens the slug tooltip on click (desktop) and dismisses it on click-away', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CourseForm {...createProps} />, {
      appContext: { localeMessages },
    });

    expect(screen.queryByText(localeMessages.slug_tooltip)).not.toBeInTheDocument();

    await user.click(screen.getByLabelText(/Slug/));
    expect(screen.getByText(localeMessages.slug_tooltip)).toBeInTheDocument();

    await user.click(document.body);
    await waitFor(() => expect(screen.queryByText(localeMessages.slug_tooltip)).not.toBeInTheDocument());
  });

  it('opens an info tooltip on click and dismisses it on click-away', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CourseForm {...createProps} />, {
      appContext: { localeMessages },
    });

    expect(screen.queryByText(localeMessages.imap_connection_tooltip)).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: localeMessages.imap_connection_tooltip }));
    expect(screen.getByText(localeMessages.imap_connection_tooltip)).toBeInTheDocument();

    await user.click(document.body);
    await waitFor(() => expect(screen.queryByText(localeMessages.imap_connection_tooltip)).not.toBeInTheDocument());
  });
});

describe('CourseForm organization footer toggle', () => {
  const editCourseData = {
    title: 'Existing Course',
    slug: 'existing-slug',
    description: 'A description.',
    target_audience: '',
    language: 'en',
    is_public: true,
    send_certificate: true,
    show_organization_footer: false,
    from_email_type: 'platform_default',
    image: null,
    image_path: null,
    imap_connection_id: null,
    newsletter_id: null,
    external_references: [],
    instructors: [],
  };

  it('sends show_organization_footer in the update payload when toggled on', async () => {
    global.fetch.mockImplementation((url, options) => {
      if (options?.method === 'POST') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ ...editCourseData, show_organization_footer: true }) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(editCourseData) });
    });
    const user = userEvent.setup();
    renderWithProviders(
      <CourseForm {...createProps} createMode={false} courseId="1" />,
      { appContext: { localeMessages: { ...localeMessages, update: 'Update', course_show_organization_footer: 'Show organization branding in email footer' } } }
    );

    const toggle = await screen.findByLabelText('Show organization branding in email footer');
    expect(toggle).not.toBeChecked();
    await user.click(toggle);
    await user.click(screen.getByRole('button', { name: 'Update' }));

    await waitFor(() => {
      const postCall = global.fetch.mock.calls.find(([, opts]) => opts?.method === 'POST');
      expect(postCall).toBeTruthy();
      expect(JSON.parse(postCall[1].body)).toMatchObject({ show_organization_footer: true });
    });
  });
});

describe('CourseForm description character limit', () => {
  it('shows a live character counter and caps input at 1000 characters', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CourseForm {...createProps} />, {
      appContext: { localeMessages: { ...localeMessages, course_description: 'Course Description' } },
    });

    const descriptionField = screen.getByLabelText(/Course Description/);
    expect(descriptionField).toHaveAttribute('maxlength', '1000');
    expect(screen.getByText('0/1000 characters used.')).toBeInTheDocument();

    await user.type(descriptionField, 'Hello world');
    expect(screen.getByText('11/1000 characters used.')).toBeInTheDocument();
  });
});

describe('CourseForm certificate fields', () => {
  const certificateLocaleMessages = {
    ...localeMessages,
    update: 'Update',
    create: 'Create',
    remove: 'Remove',
    course_send_certificate: 'Send Certificate on Completion',
    certificate_fields: 'Certificate Fields',
    add_certificate_field: 'Add Field',
    certificate_field_label: 'Label',
    certificate_field_value: 'Value',
    certificate_field_label_required_helper_text: 'A label is required when a certificate field value is provided.',
    certificate_field_value_required_helper_text: 'A value is required when a certificate field label is provided.',
  };

  const editCourseData = {
    title: 'Existing Course',
    slug: 'existing-slug',
    description: 'A description.',
    target_audience: '',
    language: 'en',
    is_public: true,
    send_certificate: true,
    show_organization_footer: false,
    from_email_type: 'platform_default',
    image: null,
    image_path: null,
    imap_connection_id: null,
    newsletter_id: null,
    external_references: [],
    certificate_fields: [{ label: 'CPD Points', value: '5' }],
    instructors: [],
  };

  it('hides the certificate fields section while the certificate is switched off', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CourseForm {...createProps} />, {
      appContext: { localeMessages: certificateLocaleMessages },
    });

    expect(screen.getByText('Certificate Fields')).toBeInTheDocument();

    await user.click(screen.getByLabelText('Send Certificate on Completion'));

    expect(screen.queryByText('Certificate Fields')).not.toBeInTheDocument();
  });

  it('stops adding fields at four', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CourseForm {...createProps} />, {
      appContext: { localeMessages: certificateLocaleMessages },
    });

    const addButton = screen.getByRole('button', { name: 'Add Field' });
    for (let index = 0; index < 4; index += 1) {
      await user.click(addButton);
    }

    expect(screen.getAllByLabelText('Label')).toHaveLength(4);
    expect(addButton).toBeDisabled();
  });

  it('sends the certificate fields in the create payload', async () => {
    global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ id: 1 }) });
    const user = userEvent.setup();
    renderWithProviders(<CourseForm {...createProps} />, {
      appContext: {
        localeMessages: { ...certificateLocaleMessages, course_description: 'Course Description' },
        languageOptions: [{ value: 'en', label: 'English' }],
      },
    });

    await user.type(screen.getByLabelText(/Course Title/), 'Python Course');
    await user.type(screen.getByLabelText(/Course Description/), 'A description.');
    await user.click(screen.getByRole('button', { name: 'Add Field' }));
    await user.type(screen.getByLabelText('Label'), 'CPD Points');
    await user.type(screen.getByLabelText('Value'), '5');
    await user.click(screen.getByRole('button', { name: 'Create' }));

    await waitFor(() => {
      const postCall = global.fetch.mock.calls.find(([, opts]) => opts?.method === 'POST');
      expect(postCall).toBeTruthy();
      expect(JSON.parse(postCall[1].body)).toMatchObject({
        certificate_fields: [{ label: 'CPD Points', value: '5' }],
      });
    });
  });

  it('refuses to save a field that has a label but no value', async () => {
    global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ id: 1 }) });
    const user = userEvent.setup();
    renderWithProviders(<CourseForm {...createProps} />, {
      appContext: {
        localeMessages: { ...certificateLocaleMessages, course_description: 'Course Description' },
        languageOptions: [{ value: 'en', label: 'English' }],
      },
    });

    await user.type(screen.getByLabelText(/Course Title/), 'Python Course');
    await user.type(screen.getByLabelText(/Course Description/), 'A description.');
    await user.click(screen.getByRole('button', { name: 'Add Field' }));
    await user.type(screen.getByLabelText('Label'), 'CPD Points');
    await user.click(screen.getByRole('button', { name: 'Create' }));

    expect(
      screen.getByText('A value is required when a certificate field label is provided.')
    ).toBeInTheDocument();
    expect(global.fetch.mock.calls.find(([, opts]) => opts?.method === 'POST')).toBeFalsy();
  });

  it('loads the saved fields in edit mode and sends the replacement list', async () => {
    global.fetch.mockImplementation((url, options) => {
      if (options?.method === 'POST') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(editCourseData) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(editCourseData) });
    });
    const user = userEvent.setup();
    renderWithProviders(
      <CourseForm {...createProps} createMode={false} courseId="1" />,
      { appContext: { localeMessages: certificateLocaleMessages } }
    );

    const valueField = await screen.findByLabelText('Value');
    expect(await screen.findByLabelText('Label')).toHaveValue('CPD Points');
    expect(valueField).toHaveValue('5');

    await user.clear(valueField);
    await user.type(valueField, '10');
    await user.click(screen.getByRole('button', { name: 'Update' }));

    await waitFor(() => {
      const postCall = global.fetch.mock.calls.find(([, opts]) => opts?.method === 'POST');
      expect(postCall).toBeTruthy();
      expect(JSON.parse(postCall[1].body)).toMatchObject({
        certificate_fields: [{ label: 'CPD Points', value: '10' }],
      });
    });
  });

  it('leaves the saved fields untouched when the certificate is switched off', async () => {
    global.fetch.mockImplementation((url, options) => {
      if (options?.method === 'POST') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(editCourseData) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(editCourseData) });
    });
    const user = userEvent.setup();
    renderWithProviders(
      <CourseForm {...createProps} createMode={false} courseId="1" />,
      { appContext: { localeMessages: certificateLocaleMessages } }
    );

    await user.click(await screen.findByLabelText('Send Certificate on Completion'));
    await user.click(screen.getByRole('button', { name: 'Update' }));

    await waitFor(() => {
      const postCall = global.fetch.mock.calls.find(([, opts]) => opts?.method === 'POST');
      expect(postCall).toBeTruthy();
      const body = JSON.parse(postCall[1].body);
      expect(body).toMatchObject({ send_certificate: false });
      expect(body).not.toHaveProperty('certificate_fields');
    });
  });
});
