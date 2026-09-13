import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import LearnerPath from '../../../platform/learners/components/LearnerPath.jsx';

vi.mock('../../render.jsx');

const localeMessages = {
    learner_path: 'Path taken',
    main_path: 'Main path',
    path_status_delivered: 'Sent',
    path_status_scheduled: 'Scheduled',
    path_status_not_sent: 'Not sent',
};

const path = [
    { course_content_id: 1, title: 'Intro', type: 'lesson', track_id: null, track_name: null, status: 'delivered' },
    { course_content_id: 2, title: 'Checkpoint', type: 'quiz', track_id: null, track_name: null, status: 'delivered' },
    { course_content_id: 10, title: 'Remedial 1', type: 'lesson', track_id: 7, track_name: 'Remedial', status: 'delivered' },
    { course_content_id: 11, title: 'Remedial 2', type: 'lesson', track_id: 7, track_name: 'Remedial', status: 'scheduled' },
];

describe('LearnerPath', () => {
    it('groups the route by the track each part was on', () => {
        renderWithProviders(<LearnerPath path={path} />, { appContext: { localeMessages } });

        const groups = screen.getAllByRole('group');
        expect(groups.map((group) => group.getAttribute('aria-label'))).toEqual(['Main path', 'Remedial']);
        expect(within(groups[1]).getByText('Remedial 1')).toBeInTheDocument();
        expect(within(groups[1]).getByText('Remedial 2')).toBeInTheDocument();
    });

    it('says which content was sent and which is still scheduled', () => {
        renderWithProviders(<LearnerPath path={path} />, { appContext: { localeMessages } });

        expect(screen.getByLabelText('Intro: Sent')).toBeInTheDocument();
        expect(screen.getByLabelText('Remedial 2: Scheduled')).toBeInTheDocument();
    });

    it('renders nothing for an empty path', () => {
        renderWithProviders(<LearnerPath path={[]} />, { appContext: { localeMessages } });

        expect(screen.queryByText('Path taken')).not.toBeInTheDocument();
    });
});
