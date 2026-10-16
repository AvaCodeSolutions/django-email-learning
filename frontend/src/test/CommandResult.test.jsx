import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { CommandResult } from '../../personalised/command_result/CommandResult.jsx';

vi.mock('../render.jsx');

const confirmContext = {
    confirmationMessage: 'Are you sure you want to unsubscribe from our mailing list?',
    confirmUrl: '/my/unsubscribe/',
    confirmToken: 'tok-123',
    localeMessages: {
        Unsubscribe: 'Unsubscribe',
        confirm_checkbox_label: 'Yes, unsubscribe me from this course',
    },
};

describe('CommandResult unsubscribe confirmation', () => {
    it('renders a POST form pointing at confirmUrl with the token and CSRF hidden fields', () => {
        const { container } = renderWithProviders(<CommandResult />, { appContext: confirmContext });

        const form = container.querySelector('form');
        expect(form).toHaveAttribute('method', 'post');
        expect(form).toHaveAttribute('action', '/my/unsubscribe/');
        expect(container.querySelector('input[name="token"]')).toHaveValue('tok-123');
        expect(container.querySelector('input[name="csrfmiddlewaretoken"]')).toBeInTheDocument();
    });

    it('gates submission behind a required, initially-unchecked confirm checkbox', () => {
        renderWithProviders(<CommandResult />, { appContext: confirmContext });

        const checkbox = screen.getByRole('checkbox', {
            name: 'Yes, unsubscribe me from this course',
        });
        expect(checkbox).not.toBeChecked();
        expect(checkbox).toBeRequired();
        expect(checkbox).toHaveAttribute('name', 'confirm');
    });

    it('labels the submit button "Unsubscribe" and does not submit on mount', () => {
        const submitSpy = vi.fn((event) => event.preventDefault());
        const { container } = renderWithProviders(<CommandResult />, { appContext: confirmContext });
        container.querySelector('form').addEventListener('submit', submitSpy);

        expect(screen.getByRole('button', { name: 'Unsubscribe' })).toHaveAttribute('type', 'submit');
        expect(submitSpy).not.toHaveBeenCalled();
    });

    it('shows the confirm-required warning when the server bounced a submission', () => {
        renderWithProviders(<CommandResult />, {
            appContext: {
                ...confirmContext,
                localeMessages: {
                    ...confirmContext.localeMessages,
                    confirm_required_message: 'Please tick the box to confirm, then choose Unsubscribe.',
                },
            },
        });

        expect(
            screen.getByText('Please tick the box to confirm, then choose Unsubscribe.')
        ).toBeInTheDocument();
    });

    it('renders the success state without a form', () => {
        const { container } = renderWithProviders(<CommandResult />, {
            appContext: {
                successMessage: 'You have been successfully unsubscribed from our mailing list.',
                localeMessages: { close_window_message: 'You can now close this window.' },
            },
        });

        expect(
            screen.getByText('You have been successfully unsubscribed from our mailing list.')
        ).toBeInTheDocument();
        expect(container.querySelector('form')).toBeNull();
    });
});

describe('CommandResult enrollment verified', () => {
    const verifiedContext = {
        successMessage: 'Your enrollment has been successfully verified.',
        localeMessages: {
            close_window_message: 'You can now close this window.',
            share_after_enrollment: 'Know someone who would enjoy this course? Share it with them.',
        },
    };

    it('invites the learner to share a public course instead of closing the window', () => {
        renderWithProviders(<CommandResult />, {
            appContext: { ...verifiedContext, shareUrl: 'https://example.com/acme/intro/', shareTitle: 'Intro' },
        });

        expect(screen.getByText('Know someone who would enjoy this course? Share it with them.')).toBeInTheDocument();
        expect(screen.getByRole('link', { name: 'Share on LinkedIn' })).toHaveAttribute(
            'href',
            expect.stringContaining(encodeURIComponent('https://example.com/acme/intro/'))
        );
        expect(screen.queryByText('You can now close this window.')).toBeNull();
    });

    it('falls back to the close-window hint when the course has no public page', () => {
        renderWithProviders(<CommandResult />, { appContext: { ...verifiedContext, shareUrl: null } });

        expect(screen.getByText('You can now close this window.')).toBeInTheDocument();
        expect(screen.queryByRole('link', { name: 'Share on LinkedIn' })).toBeNull();
    });

    it('never offers sharing on an error page', () => {
        renderWithProviders(<CommandResult />, {
            appContext: {
                errorMessage: 'An error occurred during enrollment verification.',
                ref: 'abc',
                shareUrl: 'https://example.com/acme/intro/',
                localeMessages: verifiedContext.localeMessages,
            },
        });

        expect(screen.queryByRole('link', { name: 'Share on LinkedIn' })).toBeNull();
        expect(screen.getByText('You can now close this window.')).toBeInTheDocument();
    });
});
