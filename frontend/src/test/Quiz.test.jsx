import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import { Quiz } from '../../personalised/quiz_public/Quiz.jsx';

vi.mock('../render.jsx');

const sampleQuiz = {
    id: 1,
    title: 'Sample Quiz',
    is_blocking: true,
    questions: [
        {
            id: 10,
            text: 'What is 2 + 2?',
            answers: [
                { id: 100, text: 'Three' },
                { id: 101, text: 'Four' },
            ],
        },
        {
            id: 11,
            text: 'What color is the sky?',
            answers: [
                { id: 200, text: 'Blue' },
                { id: 201, text: 'Green' },
            ],
        },
    ],
};

const sampleLocaleMessages = {
    quiz_intro: 'Select all correct answers.',
    no_answer_warning: 'You have not selected any answers.',
    your_score: 'Your score',
    error_loading_quiz: 'Error loading quiz',
    ready_to_submit: 'Ready to submit?',
    submit_quiz_note: 'Note about negative marking.',
    cancel: 'Cancel',
    submit: 'Submit',
    try_again: 'Try Again',
    close_window_message: 'You can now close this window!',
    non_blocking_quiz_caption: 'This quiz is for practice.',
    correct_answer: 'Correct answer',
    error: 'Error',
};

const defaultAppContext = {
    quiz: sampleQuiz,
    token: 'test-token',
    csrfToken: 'csrf-token',
    apiEndpoint: '/api/quiz/submit/',
    localeMessages: sampleLocaleMessages,
    direction: 'ltr',
};

describe('Quiz', () => {
    beforeEach(() => {
        global.fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ passed: true, score: 80, message: 'Well done!', is_invalidated: true }),
        });
    });

    it('renders the quiz title', () => {
        renderWithProviders(<Quiz />, { appContext: defaultAppContext });
        expect(screen.getByText('Sample Quiz')).toBeInTheDocument();
    });

    it('renders all quiz questions', () => {
        renderWithProviders(<Quiz />, { appContext: defaultAppContext });
        expect(screen.getByText('What is 2 + 2?')).toBeInTheDocument();
        expect(screen.getByText('What color is the sky?')).toBeInTheDocument();
    });

    it('renders quiz intro text', () => {
        renderWithProviders(<Quiz />, { appContext: defaultAppContext });
        expect(screen.getByText('Select all correct answers.')).toBeInTheDocument();
    });

    it('renders answer checkboxes for each question', () => {
        renderWithProviders(<Quiz />, { appContext: defaultAppContext });
        expect(screen.getByText('Three')).toBeInTheDocument();
        expect(screen.getByText('Four')).toBeInTheDocument();
        expect(screen.getByText('Blue')).toBeInTheDocument();
        expect(screen.getByText('Green')).toBeInTheDocument();
    });

    it('renders the submit button', () => {
        renderWithProviders(<Quiz />, { appContext: defaultAppContext });
        expect(screen.getByRole('button', { name: 'Submit' })).toBeInTheDocument();
    });

    it('opens the confirmation dialog when submit is clicked', () => {
        renderWithProviders(<Quiz />, { appContext: defaultAppContext });
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
        expect(screen.getByText('Ready to submit?')).toBeInTheDocument();
    });

    it('shows a warning when submitting with no answers selected', () => {
        renderWithProviders(<Quiz />, { appContext: defaultAppContext });
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
        expect(screen.getByText('You have not selected any answers.')).toBeInTheDocument();
    });

    it('does not show warning when at least one answer is selected', () => {
        renderWithProviders(<Quiz />, { appContext: defaultAppContext });
        const checkboxes = screen.getAllByRole('checkbox');
        fireEvent.click(checkboxes[0]);
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
        expect(screen.queryByText('You have not selected any answers.')).not.toBeInTheDocument();
    });

    it('closes the dialog when Cancel is clicked', async () => {
        renderWithProviders(<Quiz />, { appContext: defaultAppContext });
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
        expect(screen.getByText('Ready to submit?')).toBeInTheDocument();
        fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
        await waitFor(() =>
            expect(screen.queryByText('Ready to submit?')).not.toBeInTheDocument()
        );
    });

    it('shows score and passed message after successful submission', async () => {
        renderWithProviders(<Quiz />, { appContext: defaultAppContext });
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
        fireEvent.click(screen.getAllByRole('button', { name: 'Submit' }).at(-1));
        await waitFor(() => expect(screen.getByText(/Well done!/)).toBeInTheDocument());
        expect(screen.getByText(/80%/)).toBeInTheDocument();
    });

    it('posts to the api endpoint on submission', async () => {
        renderWithProviders(<Quiz />, { appContext: defaultAppContext });
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
        fireEvent.click(screen.getAllByRole('button', { name: 'Submit' }).at(-1));
        await waitFor(() => expect(global.fetch).toHaveBeenCalledOnce());
        const [url, options] = global.fetch.mock.calls[0];
        expect(url).toBe('/api/quiz/submit/');
        expect(options.method).toBe('POST');
        expect(options.headers['X-CSRFToken']).toBe('csrf-token');
    });

    it('shows error alert when errorMessage is present', () => {
        renderWithProviders(<Quiz />, {
            appContext: { ...defaultAppContext, errorMessage: 'Quiz not found', ref: 'abc123' },
        });
        expect(screen.getByText(/Quiz not found/)).toBeInTheDocument();
        expect(screen.getByText(/abc123/)).toBeInTheDocument();
    });

    it('shows non-blocking caption after submission for non-blocking quiz', async () => {
        const nonBlockingContext = {
            ...defaultAppContext,
            quiz: { ...sampleQuiz, is_blocking: false },
        };
        renderWithProviders(<Quiz />, { appContext: nonBlockingContext });
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
        fireEvent.click(screen.getAllByRole('button', { name: 'Submit' }).at(-1));
        await waitFor(() => expect(screen.getByText(/Well done!/)).toBeInTheDocument());
        expect(screen.getByText('This quiz is for practice.')).toBeInTheDocument();
    });

    it('shows close window message after invalidated submission', async () => {
        renderWithProviders(<Quiz />, { appContext: defaultAppContext });
        fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
        fireEvent.click(screen.getAllByRole('button', { name: 'Submit' }).at(-1));
        await waitFor(() => expect(screen.getByText('You can now close this window!')).toBeInTheDocument());
    });
});
