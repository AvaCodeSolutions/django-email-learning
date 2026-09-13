import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import LessonForm from '../../../platform/course/components/LessonForm.jsx';
import QuizForm from '../../../platform/course/components/QuizForm.jsx';
import AssignmentForm from '../../../platform/course/components/AssignmentForm.jsx';

vi.mock('../../render.jsx');

const localeMessages = {
    content_track: 'Track',
    main_path: 'Main path',
    save_lesson: 'Save Lesson',
    save_quiz: 'Save Quiz',
    save_assignment: 'Save Assignment',
    back: 'Back',
    cancel: 'Cancel',
    save_failed: 'Unable to save.',
    error_updating_quiz: 'Error updating quiz',
};

const tracks = [{ id: 7, name: 'Remedial', parent_track_id: null, merge_into_id: null }];
const appContext = { apiBaseUrl: '/api', localeMessages, userRole: 'editor', quizDefaults: {} };

const lastBody = () => JSON.parse(global.fetch.mock.calls.at(-1)[1].body);
const respondWith = (body, status = 200) => global.fetch.mockResolvedValue({
    ok: status < 400, status, json: () => Promise.resolve(body),
});

async function pickTrack(user, name) {
    await user.click(screen.getByRole('combobox', { name: 'Track' }));
    await user.click(screen.getByRole('option', { name }));
}

const quizProps = {
    quizId: 9,
    contentId: 3,
    courseId: 5,
    initialTitle: 'Checkpoint',
    initialRequiredScore: 70,
    initialIsBlocking: true,
    initialQuestions: [{
        id: 1,
        text: 'Q?',
        options: [{ id: 1, optionText: 'A', isCorrect: true }, { id: 2, optionText: 'B', isCorrect: false }],
    }],
    cancelCallback: vi.fn(),
    successCallback: vi.fn(),
    tracks,
};

describe('choosing a track on the content forms', () => {
    beforeEach(() => {
        window.localStorage.setItem('activeOrganizationId', '1');
    });

    it('offers no track choice on a course without tracks', () => {
        renderWithProviders(
            <LessonForm header="New Lesson" courseId="5" cancelCallback={vi.fn()} successCallback={vi.fn()} />,
            { appContext },
        );

        expect(screen.queryByRole('combobox', { name: 'Track' })).not.toBeInTheDocument();
    });

    it('creates a lesson on the chosen track', async () => {
        respondWith({ id: 30, lesson: { id: 4 } });
        const user = userEvent.setup();
        renderWithProviders(
            <LessonForm header="New Lesson" courseId="5" initialTitle="Catch-up" initialContent="<p>Body</p>" tracks={tracks} cancelCallback={vi.fn()} successCallback={vi.fn()} />,
            { appContext },
        );

        await pickTrack(user, 'Remedial');
        await user.click(screen.getByRole('button', { name: 'Save Lesson' }));

        await waitFor(() => expect(global.fetch).toHaveBeenCalled());
        expect(lastBody().track_id).toBe(7);
    });

    it('creates a lesson on the main path without naming a track', async () => {
        respondWith({ id: 30, lesson: { id: 4 } });
        const user = userEvent.setup();
        renderWithProviders(
            <LessonForm header="New Lesson" courseId="5" initialTitle="Intro" initialContent="<p>Body</p>" tracks={tracks} cancelCallback={vi.fn()} successCallback={vi.fn()} />,
            { appContext },
        );

        await user.click(screen.getByRole('button', { name: 'Save Lesson' }));

        await waitFor(() => expect(global.fetch).toHaveBeenCalled());
        expect(lastBody()).not.toHaveProperty('track_id');
    });

    it('moves a quiz back to the main path when its track is changed', async () => {
        respondWith({ id: 3 });
        const user = userEvent.setup();
        renderWithProviders(<QuizForm {...quizProps} initialTrackId={7} />, { appContext });

        expect(screen.getByRole('combobox', { name: 'Track' })).toHaveTextContent('Remedial');
        await pickTrack(user, 'Main path');
        await user.click(screen.getByRole('button', { name: 'Save Quiz' }));

        await waitFor(() => expect(global.fetch).toHaveBeenCalled());
        expect(lastBody()).toHaveProperty('track_id', null);
    });

    it('leaves the track out of an update that did not change it', async () => {
        respondWith({ id: 3 });
        const user = userEvent.setup();
        renderWithProviders(<QuizForm {...quizProps} initialTrackId={7} />, { appContext });

        await user.click(screen.getByRole('button', { name: 'Save Quiz' }));

        await waitFor(() => expect(global.fetch).toHaveBeenCalled());
        expect(lastBody()).not.toHaveProperty('track_id');
    });

    it('shows why the server refused to move an assignment', async () => {
        respondWith({ error: 'A track cannot merge into its own content.' }, 409);
        const user = userEvent.setup();
        renderWithProviders(
            <AssignmentForm courseId={5} assignmentId={2} contentId={4} initialTitle="Essay" initialDescription="Write it" tracks={tracks} cancelCallback={vi.fn()} successCallback={vi.fn()} />,
            { appContext },
        );

        await pickTrack(user, 'Remedial');
        await user.click(screen.getByRole('button', { name: 'Save Assignment' }));

        expect(await screen.findByText('A track cannot merge into its own content.')).toBeInTheDocument();
        expect(lastBody().track_id).toBe(7);
    });
});
