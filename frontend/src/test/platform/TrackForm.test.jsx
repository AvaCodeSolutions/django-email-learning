import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import TrackForm from '../../../platform/course/components/TrackForm';

vi.mock('../../render.jsx');

const localeMessages = {
    new_track: 'New Track',
    edit_track: 'Edit Track',
    track_name: 'Track name',
    track_name_required: 'A track needs a name.',
    track_branches_off: 'Branches off',
    track_rejoins_at: 'Rejoins the course at',
    main_path: 'Main path',
    ends_the_course: 'Ends the course',
    save_track: 'Save Track',
    cancel: 'Cancel',
    track_save_failed: 'Could not save the track.',
};

const tracks = [
    { id: 7, name: 'Remedial', parent_track_id: null, merge_into_id: null },
    { id: 8, name: 'Sibling', parent_track_id: null, merge_into_id: null },
    { id: 9, name: 'Nested', parent_track_id: 7, merge_into_id: null },
];

const contents = [
    { id: 1, title: 'Intro', track_id: null },
    { id: 3, title: 'Wrap up', track_id: null },
    { id: 10, title: 'Remedial lesson', track_id: 7 },
    { id: 11, title: 'Sibling lesson', track_id: 8 },
];

function setup(props = {}) {
    window.localStorage.setItem('activeOrganizationId', '1');
    const successCallback = vi.fn();
    renderWithProviders(
        <TrackForm courseId={5} tracks={tracks} contents={contents} cancelCallback={vi.fn()} successCallback={successCallback} {...props} />,
        { appContext: { apiBaseUrl: '/api', localeMessages, userRole: 'editor' } },
    );
    return { successCallback };
}

const optionNames = () => screen.getAllByRole('option').map((option) => option.textContent);

describe('TrackForm', () => {
    it('creates a track with the rejoin point chosen', async () => {
        global.fetch.mockResolvedValue({ ok: true, status: 201, json: () => Promise.resolve({ id: 12 }) });
        const user = userEvent.setup();
        const { successCallback } = setup();

        await user.type(screen.getByLabelText(/Track name/), 'Catch-up');
        await user.click(screen.getByRole('combobox', { name: 'Rejoins the course at' }));
        await user.click(screen.getByRole('option', { name: 'Wrap up (Main path)' }));
        await user.click(screen.getByRole('button', { name: 'Save Track' }));

        const [url, options] = global.fetch.mock.calls[0];
        expect(url).toBe('/api/organizations/1/courses/5/tracks/');
        expect(JSON.parse(options.body)).toEqual({ name: 'Catch-up', parent_track_id: null, merge_into_id: 3 });
        expect(successCallback).toHaveBeenCalled();
    });

    it('asks for a name before saving', async () => {
        const user = userEvent.setup();
        setup();

        await user.click(screen.getByRole('button', { name: 'Save Track' }));

        expect(screen.getByText('A track needs a name.')).toBeInTheDocument();
        expect(global.fetch).not.toHaveBeenCalled();
    });

    it('offers only rejoin points on the main path and the tracks it branches off', async () => {
        const user = userEvent.setup();
        setup();

        await user.click(screen.getByRole('combobox', { name: 'Branches off' }));
        await user.click(screen.getByRole('option', { name: 'Remedial' }));
        await user.click(screen.getByRole('combobox', { name: 'Rejoins the course at' }));

        expect(optionNames()).toEqual(['Ends the course', 'Intro (Main path)', 'Wrap up (Main path)', 'Remedial lesson (Remedial)']);
    });

    it('does not offer a track, or anything nested under it, as its own parent', async () => {
        const user = userEvent.setup();
        setup({ track: tracks[0] });

        await user.click(screen.getByRole('combobox', { name: 'Branches off' }));

        expect(optionNames()).toEqual(['Main path', 'Sibling']);
    });

    it('saves an existing track at its own address', async () => {
        global.fetch.mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve({ id: 7 }) });
        const user = userEvent.setup();
        setup({ track: tracks[0] });

        await user.click(screen.getByRole('button', { name: 'Save Track' }));

        expect(global.fetch.mock.calls[0][0]).toBe('/api/organizations/1/courses/5/tracks/7/');
    });

    it('shows why the server refused the track', async () => {
        global.fetch.mockResolvedValue({
            ok: false,
            status: 400,
            json: () => Promise.resolve({ error: ['A track can only merge into the main spine or a track it branches off.'] }),
        });
        const user = userEvent.setup();
        setup({ track: tracks[0] });

        await user.click(screen.getByRole('button', { name: 'Save Track' }));

        expect(await screen.findByText(/can only merge into the main spine/)).toBeInTheDocument();
    });
});
