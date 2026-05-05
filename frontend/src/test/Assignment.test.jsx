import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { Assignment } from '../../personalised/assignment_public/Assignment.jsx';

vi.mock('../render.jsx');

const sampleAssignment = {
    id: 1,
    title: 'Write a Report',
    description: 'Write a short report about React.',
    requires_text_submission: true,
    requires_file_submission: false,
};

const sampleLocaleMessages = {
    text_submission_label: 'Your Answer',
    file_submission_label: 'Upload Your File',
    submission_success: 'Your assignment has been submitted successfully!',
    submission_error: 'An error occurred while submitting your assignment.',
    submit: 'Submit',
    close_window_message: 'You can now close this window!',
    text_submission_required: 'Text submission is required.',
    file_submission_required: 'File submission is required.',
    error: 'Error',
};

const defaultAppContext = {
    assignment: sampleAssignment,
    token: 'test-token',
    csrfToken: 'csrf-token',
    apiEndpoint: '/api/assignment/submit/',
    fileUploadApiEndpoint: '/api/file/upload/',
    localeMessages: sampleLocaleMessages,
    direction: 'ltr',
};

describe('Assignment', () => {
    beforeEach(() => {
        global.fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ message: 'Submitted!' }),
        });
    });

    it('renders the assignment title', () => {
        renderWithProviders(<Assignment />, { appContext: defaultAppContext });
        expect(screen.getByText('Write a Report')).toBeInTheDocument();
    });

    it('renders the assignment description', () => {
        renderWithProviders(<Assignment />, { appContext: defaultAppContext });
        expect(screen.getByText('Write a short report about React.')).toBeInTheDocument();
    });

    it('renders the text submission field when requires_text_submission is true', () => {
        renderWithProviders(<Assignment />, { appContext: defaultAppContext });
        expect(screen.getByLabelText('Your Answer')).toBeInTheDocument();
    });

    it('does not render the text submission field when requires_text_submission is false', () => {
        const ctx = {
            ...defaultAppContext,
            assignment: { ...sampleAssignment, requires_text_submission: false },
        };
        renderWithProviders(<Assignment />, { appContext: ctx });
        expect(screen.queryByLabelText('Your Answer')).not.toBeInTheDocument();
    });

    it('renders the file upload section when requires_file_submission is true', () => {
        const ctx = {
            ...defaultAppContext,
            assignment: {
                ...sampleAssignment,
                requires_text_submission: false,
                requires_file_submission: true,
            },
        };
        renderWithProviders(<Assignment />, { appContext: ctx });
        const fileLabels = screen.getAllByText('Upload Your File');
        expect(fileLabels.length).toBeGreaterThan(0);
    });

    it('renders the submit button', () => {
        renderWithProviders(<Assignment />, { appContext: defaultAppContext });
        expect(screen.getByRole('button', { name: 'Submit' })).toBeInTheDocument();
    });

    it('shows a validation error when text is required but empty', async () => {
        renderWithProviders(<Assignment />, { appContext: defaultAppContext });
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
        await waitFor(() =>
            expect(screen.getByText('Text submission is required.')).toBeInTheDocument()
        );
        expect(global.fetch).not.toHaveBeenCalled();
    });

    it('shows success message after successful submission', async () => {
        renderWithProviders(<Assignment />, { appContext: defaultAppContext });
        fireEvent.change(screen.getByLabelText('Your Answer'), {
            target: { value: 'My answer text' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
        await waitFor(() =>
            expect(screen.getByText('Submitted!')).toBeInTheDocument()
        );
        expect(screen.getByText('You can now close this window!')).toBeInTheDocument();
    });

    it('posts the text submission to the api endpoint', async () => {
        renderWithProviders(<Assignment />, { appContext: defaultAppContext });
        fireEvent.change(screen.getByLabelText('Your Answer'), {
            target: { value: 'My answer' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
        await waitFor(() => expect(global.fetch).toHaveBeenCalledOnce());
        const [url, options] = global.fetch.mock.calls[0];
        expect(url).toBe('/api/assignment/submit/');
        expect(options.method).toBe('POST');
        expect(options.headers['X-CSRFToken']).toBe('csrf-token');
        const body = JSON.parse(options.body);
        expect(body.text_submission).toBe('My answer');
        expect(body.token).toBe('test-token');
    });

    it('shows an error alert when submission fails', async () => {
        global.fetch.mockResolvedValue({
            ok: false,
            json: () => Promise.resolve({ error: 'Server error' }),
        });
        renderWithProviders(<Assignment />, { appContext: defaultAppContext });
        fireEvent.change(screen.getByLabelText('Your Answer'), {
            target: { value: 'My answer' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
        await waitFor(() => expect(screen.getByText('Server error')).toBeInTheDocument());
    });

    it('shows error alert when errorMessage is present', () => {
        renderWithProviders(<Assignment />, {
            appContext: { ...defaultAppContext, errorMessage: 'Link expired', ref: 'ref-xyz' },
        });
        expect(screen.getByText(/Link expired/)).toBeInTheDocument();
        expect(screen.getByText(/ref-xyz/)).toBeInTheDocument();
    });
});
