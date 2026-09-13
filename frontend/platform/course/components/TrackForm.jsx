import { useMemo, useState } from 'react';
import { Alert, Button, DialogActions, DialogContent, DialogTitle, MenuItem, TextField, Typography } from '@mui/material';
import { useAppContext } from '../../../src/render';
import apiClient from '../../../src/apiClient.js';
import { sanitizeEndpointUrl } from '../../../src/sanitizeUrl.js';
import { errorMessageFrom } from './branching.js';

/**
 * Create or edit a track.
 *
 * Rejoin choices are limited to content on the main path and on the tracks this one branches
 * off, because a track may only merge outward: the server refuses anything else, so offering
 * it would only lead to that error.
 */
const TrackForm = ({ courseId, track = null, tracks = [], contents = [], cancelCallback, successCallback }) => {
    const { localeMessages, apiBaseUrl: rawApiBaseUrl } = useAppContext();
    const apiBaseUrl = sanitizeEndpointUrl(rawApiBaseUrl);
    const organizationId = localStorage.getItem('activeOrganizationId');
    const [name, setName] = useState(track?.name ?? '');
    const [parentTrackId, setParentTrackId] = useState(track?.parent_track_id ?? '');
    const [mergeIntoId, setMergeIntoId] = useState(track?.merge_into_id ?? '');
    const [errorMessage, setErrorMessage] = useState('');
    const [saving, setSaving] = useState(false);

    const trackById = useMemo(() => new Map(tracks.map((candidate) => [candidate.id, candidate])), [tracks]);

    // The track itself and every track it branches off, innermost first.
    const chainFrom = (trackId) => {
        const chain = [];
        const seen = new Set();
        let current = trackById.get(trackId);
        while (current && !seen.has(current.id)) {
            seen.add(current.id);
            chain.push(current.id);
            current = current.parent_track_id != null ? trackById.get(current.parent_track_id) : null;
        }
        return chain;
    };

    const mergeLevelsFor = (parentValue) => new Set([null, ...(parentValue === '' ? [] : chainFrom(Number(parentValue)))]);

    // A track cannot branch off itself or off anything nested under it.
    const parentOptions = tracks.filter((candidate) => !track || !chainFrom(candidate.id).includes(track.id));
    const mergeLevels = mergeLevelsFor(parentTrackId);
    const mergeOptions = contents.filter((content) => mergeLevels.has(content.track_id ?? null));

    const trackLabel = (trackId) => (trackId == null
        ? (localeMessages['main_path'] || 'Main path')
        : (trackById.get(trackId)?.name ?? ''));

    const changeParent = (value) => {
        setParentTrackId(value);
        const levels = mergeLevelsFor(value);
        const stillOffered = contents.some((content) => content.id === Number(mergeIntoId) && levels.has(content.track_id ?? null));
        if (mergeIntoId !== '' && !stillOffered) {
            setMergeIntoId('');
        }
    };

    const save = () => {
        if (name.trim() === '') {
            setErrorMessage(localeMessages['track_name_required'] || 'A track needs a name.');
            return;
        }
        setErrorMessage('');
        setSaving(true);
        const tracksUrl = `${apiBaseUrl}/organizations/${organizationId}/courses/${courseId}/tracks/`;
        apiClient.post(track ? `${tracksUrl}${track.id}/` : tracksUrl, {
            name: name.trim(),
            parent_track_id: parentTrackId === '' ? null : Number(parentTrackId),
            merge_into_id: mergeIntoId === '' ? null : Number(mergeIntoId),
        })
            .then(() => successCallback())
            .catch((error) => {
                console.error('Error saving track:', error);
                setErrorMessage(errorMessageFrom(error, localeMessages['track_save_failed'] || 'Could not save the track.'));
            })
            .finally(() => setSaving(false));
    };

    const selectSlotProps = { select: { displayEmpty: true }, inputLabel: { shrink: true } };

    return (
        <>
            <DialogTitle>{track ? (localeMessages['edit_track'] || 'Edit Track') : (localeMessages['new_track'] || 'New Track')}</DialogTitle>
            <DialogContent>
                {localeMessages['track_form_help'] && (
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {localeMessages['track_form_help']}
                    </Typography>
                )}
                {errorMessage && <Alert severity="error" sx={{ mb: 2 }}>{errorMessage}</Alert>}
                <TextField
                    id="track-name"
                    label={localeMessages['track_name'] || 'Track name'}
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    fullWidth
                    required
                    sx={{ mt: 1, mb: 2 }}
                    slotProps={{ htmlInput: { maxLength: 200 } }}
                />
                <TextField
                    select
                    id="track-parent"
                    label={localeMessages['track_branches_off'] || 'Branches off'}
                    value={parentTrackId}
                    onChange={(event) => changeParent(event.target.value)}
                    fullWidth
                    sx={{ mb: 2 }}
                    slotProps={selectSlotProps}
                >
                    <MenuItem value="">{localeMessages['main_path'] || 'Main path'}</MenuItem>
                    {parentOptions.map((candidate) => (
                        <MenuItem key={candidate.id} value={candidate.id}>{candidate.name}</MenuItem>
                    ))}
                </TextField>
                <TextField
                    select
                    id="track-merge"
                    label={localeMessages['track_rejoins_at'] || 'Rejoins the course at'}
                    value={mergeIntoId}
                    onChange={(event) => setMergeIntoId(event.target.value)}
                    fullWidth
                    slotProps={selectSlotProps}
                >
                    <MenuItem value="">{localeMessages['ends_the_course'] || 'Ends the course'}</MenuItem>
                    {mergeOptions.map((content) => (
                        <MenuItem key={content.id} value={content.id}>{`${content.title} (${trackLabel(content.track_id)})`}</MenuItem>
                    ))}
                </TextField>
            </DialogContent>
            <DialogActions>
                <Button onClick={cancelCallback}>{localeMessages['cancel'] || 'Cancel'}</Button>
                <Button variant="contained" color="secondary" onClick={save} disabled={saving}>
                    {localeMessages['save_track'] || 'Save Track'}
                </Button>
            </DialogActions>
        </>
    );
};

export default TrackForm;
