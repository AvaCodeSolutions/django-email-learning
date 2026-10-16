import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import CourseForm from '../../../platform/courses/components/CourseForm';

vi.mock('../../render.jsx');
vi.mock('../../components/ContentEditor.jsx', () => ({
    default: ({ initialContent, contentUpdateCallback, disabled }) => (
        <textarea data-testid="email-editor" defaultValue={initialContent} disabled={disabled} onChange={(e) => contentUpdateCallback(e.target.value)} />
    ),
}));

const localeMessages = {
    course_title: 'Course Title',
    description_char_limit_helper_text: 'COUNT/1000 characters used.',
    update: 'Update',
    course_settings_tab: 'Settings',
    course_emails_tab: 'Enrollment & welcome emails',
    enrollment_confirmation_link: 'Email link',
    enrollment_confirmation_gate: 'Enrollment gate',
    enrollment_gate_key: 'Enrollment gate key',
    enrollment_gate_key_required: 'Enter a key for the enrollment gate.',
    enrollment_email: 'Enrollment email',
    enrollment_email_link_mode_info: 'Learners receive the built-in verification email.',
    welcome_email: 'Welcome email',
    email_subject: 'Subject',
    restore_default_email: 'Restore default',
    enrollment_reminder_enabled: 'Send a reminder',
    enrollment_reminder_email: 'Reminder email',
};

const DEFAULT_WELCOME = '<p>Welcome to {{ course_title }}</p>';

const courseData = (overrides = {}) => ({
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
    enrollment_confirmation: 'link',
    enrollment_gate_key: '',
    enrollment_email_subject: 'Complete your enrollment',
    enrollment_email_body: '<p>Pending</p>',
    enrollment_email_customized: false,
    enrollment_reminder_enabled: false,
    enrollment_reminder_subject: 'Still waiting',
    enrollment_reminder_body: '<p>Reminder</p>',
    enrollment_reminder_customized: false,
    default_enrollment_reminder_subject: 'Still waiting',
    default_enrollment_reminder_body: '<p>Reminder</p>',
    welcome_email_subject: 'Enrollment Verified',
    welcome_email_body: DEFAULT_WELCOME,
    welcome_email_customized: false,
    default_enrollment_email_subject: 'Complete your enrollment',
    default_enrollment_email_body: '<p>Pending</p>',
    default_welcome_email_subject: 'Enrollment Verified',
    default_welcome_email_body: DEFAULT_WELCOME,
    ...overrides,
});

function mockCourse(data) {
    global.fetch.mockImplementation((url, options) => Promise.resolve({
        ok: true,
        json: () => Promise.resolve(options?.method === 'POST' ? { ...data, ...JSON.parse(options.body) } : data),
    }));
}

async function openEmailsTab(user, props = {}) {
    renderWithProviders(
        <CourseForm successCallback={vi.fn()} failureCallback={vi.fn()} cancelCallback={vi.fn()} activeOrganizationId="1" createMode={false} courseId="1" {...props} />,
        { appContext: { localeMessages } }
    );
    await user.click(await screen.findByRole('tab', { name: 'Enrollment & welcome emails' }));
}

function postedPayload() {
    const postCall = global.fetch.mock.calls.find(([, opts]) => opts?.method === 'POST');
    return postCall ? JSON.parse(postCall[1].body) : null;
}

describe('CourseForm enrollment & welcome emails tab', () => {
    beforeEach(() => {
        global.fetch.mockReset();
    });

    it('has no tabs while creating a course', () => {
        renderWithProviders(
            <CourseForm successCallback={vi.fn()} failureCallback={vi.fn()} cancelCallback={vi.fn()} activeOrganizationId="1" createMode />,
            { appContext: { localeMessages } }
        );

        expect(screen.queryByRole('tab')).not.toBeInTheDocument();
    });

    it('keeps the verification email out of reach while enrollments are confirmed by link', async () => {
        mockCourse(courseData());
        const user = userEvent.setup();
        await openEmailsTab(user);

        expect(screen.getByRole('radio', { name: /^Email link/ })).toBeChecked();
        expect(screen.getByText('Learners receive the built-in verification email.')).toBeInTheDocument();
        expect(screen.queryByText('Enrollment email')).not.toBeInTheDocument();
        // Only the welcome email can be edited.
        const [welcomeEditor] = screen.getAllByTestId('email-editor');
        expect(welcomeEditor).toHaveValue(DEFAULT_WELCOME);
    });

    it('asks for a key before gating enrollments', async () => {
        mockCourse(courseData());
        const user = userEvent.setup();
        await openEmailsTab(user);

        await user.click(screen.getByRole('radio', { name: /^Enrollment gate/ }));
        expect(screen.getByText('Enrollment email')).toBeInTheDocument();
        await user.click(screen.getByRole('button', { name: 'Update' }));

        expect(await screen.findByText('Enter a key for the enrollment gate.')).toBeInTheDocument();
        expect(postedPayload()).toBeNull();
    });

    it('gates enrollments without freezing the default emails', async () => {
        mockCourse(courseData());
        const user = userEvent.setup();
        await openEmailsTab(user);

        await user.click(screen.getByRole('radio', { name: /^Enrollment gate/ }));
        await user.type(screen.getByLabelText(/Enrollment gate key/), 'payment');
        await user.click(screen.getByRole('button', { name: 'Update' }));

        await waitFor(() => expect(postedPayload()).not.toBeNull());
        const payload = postedPayload();
        expect(payload).toMatchObject({ enrollment_confirmation: 'gate', enrollment_gate_key: 'payment' });
        expect(payload).not.toHaveProperty('enrollment_email_body');
        expect(payload).not.toHaveProperty('welcome_email_body');
    });

    it('sends only the email that changed', async () => {
        mockCourse(courseData());
        const user = userEvent.setup();
        await openEmailsTab(user);

        const [welcomeEditor] = screen.getAllByTestId('email-editor');
        await user.clear(welcomeEditor);
        await user.type(welcomeEditor, 'Hi there');
        await user.click(screen.getByRole('button', { name: 'Update' }));

        await waitFor(() => expect(postedPayload()).not.toBeNull());
        const payload = postedPayload();
        expect(payload.welcome_email_body).toBe('Hi there');
        expect(payload).not.toHaveProperty('welcome_email_subject');
        expect(payload).not.toHaveProperty('enrollment_confirmation');
    });

    it('restores a customised email to the default by sending nulls', async () => {
        mockCourse(courseData({
            welcome_email_subject: 'Custom subject',
            welcome_email_body: '<p>Custom</p>',
            welcome_email_customized: true,
        }));
        const user = userEvent.setup();
        await openEmailsTab(user);

        expect(screen.getByDisplayValue('Custom subject')).toBeInTheDocument();
        await user.click(screen.getByRole('button', { name: 'Restore default' }));
        expect(screen.getByDisplayValue('Enrollment Verified')).toBeInTheDocument();
        await user.click(screen.getByRole('button', { name: 'Update' }));

        await waitFor(() => expect(postedPayload()).not.toBeNull());
        expect(postedPayload()).toMatchObject({ welcome_email_subject: null, welcome_email_body: null });
    });

    it('turns on the gated reminder without freezing its default text', async () => {
        mockCourse(courseData({ enrollment_confirmation: 'gate', enrollment_gate_key: 'payment' }));
        const user = userEvent.setup();
        await openEmailsTab(user);

        expect(screen.queryByText('Reminder email')).not.toBeInTheDocument();
        await user.click(screen.getByRole('switch', { name: 'Send a reminder' }));
        expect(screen.getByText('Reminder email')).toBeInTheDocument();
        await user.click(screen.getByRole('button', { name: 'Update' }));

        await waitFor(() => expect(postedPayload()).not.toBeNull());
        const payload = postedPayload();
        expect(payload.enrollment_reminder_enabled).toBe(true);
        expect(payload).not.toHaveProperty('enrollment_reminder_body');
    });

    it('offers no reminder switch while enrollments are confirmed by link', async () => {
        mockCourse(courseData());
        const user = userEvent.setup();
        await openEmailsTab(user);

        expect(screen.queryByRole('switch', { name: 'Send a reminder' })).not.toBeInTheDocument();
    });
});
