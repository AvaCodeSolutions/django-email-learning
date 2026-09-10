import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import QuizAnalytics from '../../../platform/course/components/QuizAnalytics';

vi.mock('../../render.jsx');

const localeMessages = {
    quiz_analytics_load_failed: 'Unable to load quiz analytics.',
    quiz_analytics_no_data: 'No quiz submissions have been recorded yet.',
    quiz_analytics_basis: "Based on each learner's first attempt only.",
    quiz_analytics_legacy_note: 'LEGACY_COUNT earlier submission(s) cannot be included.',
    quiz_analytics_shared_warning: 'This quiz is used by more than one course: SHARED_COURSES',
    quiz_analytics_low_sample: 'Too few responses to show percentages (fewer than MIN_RESPONSES).',
    quiz_analytics_counted: 'First attempts counted',
    quiz_analytics_total_submissions: 'Total submissions',
    quiz_analytics_repeat_attempts: 'Repeat attempts',
    quiz_analytics_asked: 'Asked',
    quiz_analytics_answered: 'Answered',
    quiz_analytics_skipped: 'Skipped',
    quiz_analytics_correct: 'Correct',
    quiz_analytics_correct_rate: 'Correct rate',
    quiz_analytics_chose: 'Chose this',
    quiz_analytics_not_asked: 'Not shown to any learner yet.',
    quiz_analytics_multiple_choice: 'Multiple choice',
    quiz_analytics_correct_definition: 'Exactly the correct options.',
};

const appContext = { apiBaseUrl: '/api', localeMessages };

const makeAnalytics = (overrides = {}) => ({
    quiz_id: 7,
    quiz_title: 'Sample Quiz',
    selection_strategy: 'random',
    basis: 'first_attempt',
    min_responses_for_rates: 5,
    total_submissions: 8,
    repeat_attempts: 2,
    counted_submissions: 6,
    legacy_submissions: 0,
    shared_with: [{ content_id: 1, course_id: 1, course_title: 'Sample Course' }],
    questions: [
        {
            id: 11,
            text: 'What is 2 + 2?',
            is_multiple_choice: false,
            asked_count: 6,
            answered_count: 6,
            skipped_count: 0,
            correct_count: 3,
            correct_rate: 0.5,
            answers: [
                { id: 101, text: 'Four', is_correct: true, selected_count: 3, selected_rate: 0.5 },
                { id: 102, text: 'Five', is_correct: false, selected_count: 3, selected_rate: 0.5 },
            ],
        },
    ],
    ...overrides,
});

const respondWith = (payload) =>
    global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(payload) });

function setup() {
    window.localStorage.setItem('activeOrganizationId', '1');
    return renderWithProviders(<QuizAnalytics quizId={7} />, { appContext });
}

describe('QuizAnalytics', () => {
    beforeEach(() => {
        respondWith(makeAnalytics());
    });

    it('requests the analytics endpoint for the given quiz', async () => {
        setup();
        await waitFor(() => expect(global.fetch).toHaveBeenCalledOnce());
        expect(global.fetch.mock.calls[0][0]).toBe('/api/organizations/1/quizzes/7/analytics/');
    });

    it('shows percentages once the sample is large enough', async () => {
        setup();
        expect(await screen.findByText('What is 2 + 2?')).toBeInTheDocument();
        expect(screen.getByText('Correct rate: 50% (3/6)')).toBeInTheDocument();
        expect(screen.getAllByText('50% (3)')).toHaveLength(2);
    });

    it('withholds percentages and shows raw counts for a low-N question', async () => {
        respondWith(
            makeAnalytics({
                counted_submissions: 2,
                total_submissions: 2,
                repeat_attempts: 0,
                questions: [
                    {
                        id: 11,
                        text: 'What is 2 + 2?',
                        is_multiple_choice: false,
                        asked_count: 2,
                        answered_count: 2,
                        skipped_count: 0,
                        correct_count: 1,
                        correct_rate: null,
                        answers: [
                            { id: 101, text: 'Four', is_correct: true, selected_count: 1, selected_rate: null },
                            { id: 102, text: 'Five', is_correct: false, selected_count: 1, selected_rate: null },
                        ],
                    },
                ],
            })
        );
        setup();

        expect(
            await screen.findByText('Too few responses to show percentages (fewer than 5).')
        ).toBeInTheDocument();
        expect(screen.getByText('Correct: 1/2')).toBeInTheDocument();
        expect(screen.queryByText(/%/)).not.toBeInTheDocument();
    });

    it('shows the empty state when nothing has been submitted', async () => {
        respondWith(
            makeAnalytics({ total_submissions: 0, counted_submissions: 0, repeat_attempts: 0, questions: [] })
        );
        setup();
        expect(
            await screen.findByText('No quiz submissions have been recorded yet.')
        ).toBeInTheDocument();
    });

    it('explains that pre-capture submissions are excluded', async () => {
        respondWith(makeAnalytics({ legacy_submissions: 4 }));
        setup();
        expect(
            await screen.findByText('4 earlier submission(s) cannot be included.')
        ).toBeInTheDocument();
    });

    it('warns when the quiz is shared across courses', async () => {
        respondWith(
            makeAnalytics({
                shared_with: [
                    { content_id: 1, course_id: 1, course_title: 'Sample Course' },
                    { content_id: 2, course_id: 2, course_title: 'Second Course' },
                ],
            })
        );
        setup();
        expect(
            await screen.findByText('This quiz is used by more than one course: Sample Course, Second Course')
        ).toBeInTheDocument();
    });

    it('marks a question that no learner has been shown', async () => {
        respondWith(
            makeAnalytics({
                questions: [
                    {
                        id: 12,
                        text: 'Brand new question?',
                        is_multiple_choice: true,
                        asked_count: 0,
                        answered_count: 0,
                        skipped_count: 0,
                        correct_count: 0,
                        correct_rate: null,
                        answers: [
                            { id: 201, text: 'A', is_correct: true, selected_count: 0, selected_rate: null },
                        ],
                    },
                ],
            })
        );
        setup();
        expect(await screen.findByText('Not shown to any learner yet.')).toBeInTheDocument();
        expect(screen.getByText('Multiple choice')).toBeInTheDocument();
    });

    it('surfaces a load failure', async () => {
        global.fetch.mockResolvedValue({ ok: false, status: 500, json: () => Promise.resolve({}) });
        setup();
        expect(await screen.findByText('Unable to load quiz analytics.')).toBeInTheDocument();
    });
});
