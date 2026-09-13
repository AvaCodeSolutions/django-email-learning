import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import CourseMap from '../../../platform/course/components/CourseMap.jsx';

vi.mock('../../render.jsx');

const localeMessages = {
    branch_condition_failed: 'If failed',
    branch_condition_default: 'Otherwise',
    rejoins_at: 'Rejoins at TITLE',
    ends_the_course: 'Ends the course',
    map_no_match: 'If no rule matches, the learner continues below.',
    map_course_complete: 'Course complete',
    not_published: 'Not published',
    course_view_map: 'Map',
    unrouted_tracks: 'Tracks no rule routes onto yet',
};

const contents = [
    { id: 1, title: 'Intro', type: 'lesson', track_id: null, is_published: true },
    { id: 10, title: 'Remedial lesson', type: 'lesson', track_id: 7, is_published: true },
    { id: 2, title: 'Checkpoint', type: 'quiz', track_id: null, is_published: true },
    { id: 3, title: 'Wrap up', type: 'lesson', track_id: null, is_published: false },
];
const remedial = { id: 7, name: 'Remedial', parent_track_id: null, merge_into_id: 3 };
const failedRule = { id: 1, source_id: 2, order: 1, condition: 'failed', threshold: null, target_id: 7 };

function renderMap(props = {}) {
    const onContentClick = vi.fn();
    renderWithProviders(
        <CourseMap contents={contents} tracks={[remedial]} transitions={[failedRule]} onContentClick={onContentClick} {...props} />,
        { appContext: { localeMessages } },
    );
    return onContentClick;
}

describe('CourseMap', () => {
    it('draws a lane for the track a branch point routes onto', () => {
        renderMap();

        const lane = screen.getByRole('group', { name: 'Remedial' });
        expect(within(lane).getByText('If failed')).toBeInTheDocument();
        expect(within(lane).getByRole('button', { name: 'Remedial lesson' })).toBeInTheDocument();
        expect(within(lane).getByText('Rejoins at Wrap up')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Intro' })).toBeInTheDocument();
        expect(screen.getByText('Course complete')).toBeInTheDocument();
    });

    it('says the learner continues down this path when no rule matches', () => {
        renderMap();

        expect(screen.getByText('If no rule matches, the learner continues below.')).toBeInTheDocument();
    });

    it('drops that note once an otherwise rule catches every result', () => {
        const advanced = { id: 8, name: 'Advanced', parent_track_id: null, merge_into_id: 3 };
        renderMap({
            tracks: [remedial, advanced],
            transitions: [failedRule, { id: 2, source_id: 2, order: 2, condition: 'default', threshold: null, target_id: 8 }],
        });

        expect(screen.getByRole('group', { name: 'Advanced' })).toBeInTheDocument();
        expect(screen.queryByText('If no rule matches, the learner continues below.')).not.toBeInTheDocument();
    });

    it('marks content that is not published', () => {
        renderMap();

        expect(screen.getByRole('button', { name: 'Wrap up (Not published)' })).toBeInTheDocument();
    });

    it('opens content when its node is clicked', async () => {
        const user = userEvent.setup();
        const onContentClick = renderMap();

        await user.click(screen.getByRole('button', { name: 'Remedial lesson' }));

        expect(onContentClick).toHaveBeenCalledWith(10);
    });

    it('keeps tracks no rule reaches on the map', () => {
        renderMap({
            contents: [...contents, { id: 20, title: 'Draft lesson', type: 'lesson', track_id: 9, is_published: true }],
            tracks: [remedial, { id: 9, name: 'Draft', parent_track_id: null, merge_into_id: null }],
        });

        expect(screen.getByText('Tracks no rule routes onto yet')).toBeInTheDocument();
        const lane = screen.getByRole('group', { name: 'Draft' });
        expect(within(lane).getByRole('button', { name: 'Draft lesson' })).toBeInTheDocument();
        expect(within(lane).getByText('Ends the course')).toBeInTheDocument();
    });
});
