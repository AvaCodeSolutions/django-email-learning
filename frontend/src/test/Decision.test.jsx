import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { Decision } from '../../personalised/decision_public/Decision.jsx';

vi.mock('../render.jsx');

const decision = {
    id: 4,
    title: 'Pick your path',
    prompt: 'Where do you want to go next?',
    options: [
        { id: 11, text: 'Basics first' },
        { id: 12, text: 'Straight to advanced' },
    ],
};

const appContext = {
    decision,
    token: 'test-token',
    csrfToken: 'csrf-token',
    apiEndpoint: '/api/decisions/',
    direction: 'ltr',
    localeMessages: {
        choose_an_answer: 'Choose one answer',
        submit: 'Submit',
        submission_error: 'Your answer could not be recorded.',
        close_window_message: 'You can now close this window!',
        error: 'Error',
    },
};

const respondWith = (body, ok = true) => global.fetch.mockResolvedValue({ ok, json: () => Promise.resolve(body) });

describe('Decision', () => {
    beforeEach(() => {
        global.fetch.mockClear();
        respondWith({ message: 'Thanks, your answer has been recorded.' });
    });

    it('shows the question and the answers to pick from', () => {
        renderWithProviders(<Decision />, { appContext });

        expect(screen.getByText('Pick your path')).toBeInTheDocument();
        expect(screen.getByText('Where do you want to go next?')).toBeInTheDocument();
        expect(screen.getByLabelText('Basics first')).toBeInTheDocument();
        expect(screen.getByLabelText('Straight to advanced')).toBeInTheDocument();
    });

    it('sends the chosen answer and confirms it was recorded', async () => {
        renderWithProviders(<Decision />, { appContext });

        fireEvent.click(screen.getByLabelText('Straight to advanced'));
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));

        expect(await screen.findByText('Thanks, your answer has been recorded.')).toBeInTheDocument();
        const [url, options] = global.fetch.mock.calls[0];
        expect(url).toBe('/api/decisions/');
        expect(JSON.parse(options.body)).toEqual({ token: 'test-token', option_id: 12 });
    });

    it('asks for an answer before sending anything', () => {
        renderWithProviders(<Decision />, { appContext });

        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));

        expect(screen.getByText('Choose one answer')).toBeInTheDocument();
        expect(global.fetch).not.toHaveBeenCalled();
    });

    it('says why an answer was refused', async () => {
        respondWith({ error: 'This question has already been answered.' }, false);
        renderWithProviders(<Decision />, { appContext });

        fireEvent.click(screen.getByLabelText('Basics first'));
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));

        expect(await screen.findByText('This question has already been answered.')).toBeInTheDocument();
    });

    it('shows the error the link was opened with instead of the question', () => {
        renderWithProviders(<Decision />, {
            appContext: { ...appContext, errorMessage: 'This question has already been answered, so the link no longer works.' },
        });

        expect(screen.getByText(/so the link no longer works/)).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Submit' })).not.toBeInTheDocument();
    });
});
