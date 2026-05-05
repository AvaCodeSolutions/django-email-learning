import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { CertificateForm } from '../../personalised/certificate_form/CertificateForm.jsx';

vi.mock('../render.jsx');

const sampleLocaleMessages = {
    form_title: 'Certificate of Completion',
    form_intro: 'Congratulations! Enter the name you would like on your certificate.',
    full_name: 'Full Name',
    full_name_required: 'Full Name is required',
    error_sending_data: 'An error occurred while sending data. Please try again later.',
    form_submission_success: 'Your certificate name has been submitted successfully!',
    submit: 'Submit',
    view_certificate: 'View Certificate',
};

const defaultAppContext = {
    localeMessages: sampleLocaleMessages,
    apiEndpoint: '/api/certificate/submit/',
    token: 'test-token',
    csrfToken: 'csrf-token',
};

describe('CertificateForm', () => {
    beforeEach(() => {
        global.fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ certificate_url: '/certificates/ORG-COURSE-42-abc123/' }),
        });
    });

    it('renders the form title', () => {
        renderWithProviders(<CertificateForm />, { appContext: defaultAppContext });
        expect(screen.getByText('Certificate of Completion')).toBeInTheDocument();
    });

    it('renders the intro text', () => {
        renderWithProviders(<CertificateForm />, { appContext: defaultAppContext });
        expect(
            screen.getByText('Congratulations! Enter the name you would like on your certificate.')
        ).toBeInTheDocument();
    });

    it('renders the full name input field', () => {
        renderWithProviders(<CertificateForm />, { appContext: defaultAppContext });
        expect(screen.getByLabelText(/Full Name/)).toBeInTheDocument();
    });

    it('renders the submit button', () => {
        renderWithProviders(<CertificateForm />, { appContext: defaultAppContext });
        expect(screen.getByRole('button', { name: 'Submit' })).toBeInTheDocument();
    });

    it('shows a validation error when name is empty', async () => {
        const { container } = renderWithProviders(<CertificateForm />, { appContext: defaultAppContext });
        fireEvent.submit(container.querySelector('form'));
        await waitFor(() =>
            expect(screen.getByText('Full Name is required')).toBeInTheDocument()
        );
        expect(global.fetch).not.toHaveBeenCalled();
    });

    it('submits the form with the entered name', async () => {
        renderWithProviders(<CertificateForm />, { appContext: defaultAppContext });
        fireEvent.change(screen.getByLabelText(/Full Name/), {
            target: { value: 'Jane Doe' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
        await waitFor(() => expect(global.fetch).toHaveBeenCalledOnce());
        const [, options] = global.fetch.mock.calls[0];
        const body = JSON.parse(options.body);
        expect(body.name).toBe('Jane Doe');
        expect(body.token).toBe('test-token');
        expect(options.headers['X-CSRFToken']).toBe('csrf-token');
    });

    it('shows success alert after successful submission', async () => {
        renderWithProviders(<CertificateForm />, { appContext: defaultAppContext });
        fireEvent.change(screen.getByLabelText(/Full Name/), {
            target: { value: 'Jane Doe' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
        await waitFor(() =>
            expect(
                screen.getByText('Your certificate name has been submitted successfully!')
            ).toBeInTheDocument()
        );
    });

    it('shows the View Certificate button after successful submission', async () => {
        renderWithProviders(<CertificateForm />, { appContext: defaultAppContext });
        fireEvent.change(screen.getByLabelText(/Full Name/), {
            target: { value: 'Jane Doe' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
        await waitFor(() =>
            expect(screen.getByRole('link', { name: 'View Certificate' })).toBeInTheDocument()
        );
        expect(screen.getByRole('link', { name: 'View Certificate' })).toHaveAttribute(
            'href',
            '/certificates/ORG-COURSE-42-abc123/'
        );
    });

    it('shows an error alert when the API call fails', async () => {
        global.fetch.mockResolvedValue({
            ok: false,
            json: () => Promise.resolve({}),
        });
        renderWithProviders(<CertificateForm />, { appContext: defaultAppContext });
        fireEvent.change(screen.getByLabelText(/Full Name/), {
            target: { value: 'Jane Doe' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
        await waitFor(() =>
            expect(
                screen.getByText('An error occurred while sending data. Please try again later.')
            ).toBeInTheDocument()
        );
    });
});
