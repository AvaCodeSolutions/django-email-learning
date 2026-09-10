import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import QuizForm from '../../../platform/course/components/QuizForm';

vi.mock('../../render.jsx');

const localeMessages = {
    new_quiz: 'New Quiz',
    update_quiz: 'Update Quiz',
    quiz_title: 'Quiz Title',
    quiz_settings: 'Quiz Settings',
    add_question: 'Add Question',
    save_quiz: 'Save Quiz',
    back: 'Back',
    quiz_tab_questions: 'Questions',
    quiz_tab_analytics: 'Analytics',
    quiz_analytics_no_data: 'No quiz submissions have been recorded yet.',
    quiz_analytics_basis: "Based on each learner's first attempt only.",
};

const appContext = { apiBaseUrl: '/api', localeMessages, userRole: 'admin', quizDefaults: {} };

const emptyAnalytics = {
    quiz_id: 7,
    quiz_title: 'Sample Quiz',
    basis: 'first_attempt',
    min_responses_for_rates: 5,
    total_submissions: 0,
    repeat_attempts: 0,
    counted_submissions: 0,
    legacy_submissions: 0,
    shared_with: [],
    questions: [],
};

function setup(props = {}) {
    window.localStorage.setItem('activeOrganizationId', '1');
    return renderWithProviders(
        <QuizForm cancelCallback={vi.fn()} successCallback={vi.fn()} courseId={5} {...props} />,
        { appContext }
    );
}

describe('QuizForm tabs', () => {
    beforeEach(() => {
        global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(emptyAnalytics) });
    });

    it('offers no Analytics tab while a quiz is still being created', () => {
        setup();
        expect(screen.getByText('New Quiz')).toBeInTheDocument();
        expect(screen.queryByRole('tab', { name: 'Analytics' })).not.toBeInTheDocument();
    });

    it('offers both tabs when editing an existing quiz', () => {
        setup({ quizId: 7, contentId: 3, initialTitle: 'Sample Quiz' });
        expect(screen.getByRole('tab', { name: 'Questions' })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: 'Analytics' })).toBeInTheDocument();
    });

    it('loads analytics only after the tab is opened', async () => {
        const user = userEvent.setup();
        setup({ quizId: 7, contentId: 3, initialTitle: 'Sample Quiz' });

        expect(global.fetch).not.toHaveBeenCalled();
        await user.click(screen.getByRole('tab', { name: 'Analytics' }));

        await waitFor(() => expect(global.fetch).toHaveBeenCalledOnce());
        expect(
            await screen.findByText('No quiz submissions have been recorded yet.')
        ).toBeInTheDocument();
    });

    it('keeps unsaved authoring edits when switching tabs and back', async () => {
        const user = userEvent.setup();
        setup({ quizId: 7, contentId: 3, initialTitle: 'Sample Quiz' });

        const titleField = screen.getByLabelText(/Quiz Title/);
        await user.clear(titleField);
        await user.type(titleField, 'Edited title');

        await user.click(screen.getByRole('tab', { name: 'Analytics' }));
        await screen.findByText('No quiz submissions have been recorded yet.');
        await user.click(screen.getByRole('tab', { name: 'Questions' }));

        expect(screen.getByLabelText(/Quiz Title/)).toHaveValue('Edited title');
    });
});
