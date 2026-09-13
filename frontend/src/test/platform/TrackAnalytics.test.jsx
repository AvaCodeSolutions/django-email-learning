import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import TrackAnalytics from '../../../platform/course/components/TrackAnalytics.jsx';

vi.mock('../../render.jsx');

const localeMessages = {
    track_breakdown_title: 'Tracks',
    content_track: 'Track',
    track_routed: 'Routed onto it',
    track_finished: 'Finished',
    track_still_on: 'Still on it',
    track_left: 'Left the course',
    track_breakdown_load_failed: 'Could not load the track numbers.',
};

const appContext = { localeMessages, analyticsBaseUrl: { base: '/api/analytics/organizations/1', orgId: 1 } };

const respondWith = (body, status = 200) => global.fetch.mockResolvedValue({
    ok: status < 400, status, json: () => Promise.resolve(body),
});

describe('TrackAnalytics', () => {
    it('shows how learners fared on each track of the course', async () => {
        respondWith({ data: [{ track_id: 7, name: 'Remedial', parent_track_id: null, routed: 4, finished: 2, still_on_track: 1, left_course: 1 }] });
        renderWithProviders(<TrackAnalytics courseId={5} />, { appContext });

        const table = await screen.findByRole('table', { name: 'Tracks' });
        const row = within(table).getByRole('row', { name: /Remedial/ });
        expect(within(row).getAllByRole('cell').map((cell) => cell.textContent)).toEqual(['4', '2', '1', '1']);
        expect(global.fetch.mock.calls[0][0]).toBe('/api/analytics/organizations/1/track-breakdown/?course_id=5');
    });

    it('renders nothing for a course without tracks', async () => {
        respondWith({ data: [] });
        renderWithProviders(<TrackAnalytics courseId={5} />, { appContext });

        await waitFor(() => expect(global.fetch).toHaveBeenCalled());
        expect(screen.queryByText('Tracks')).not.toBeInTheDocument();
    });

    it('says so when the numbers fail to load', async () => {
        respondWith({ error: 'boom' }, 500);
        renderWithProviders(<TrackAnalytics courseId={5} />, { appContext });

        expect(await screen.findByText('Could not load the track numbers.')).toBeInTheDocument();
    });
});
