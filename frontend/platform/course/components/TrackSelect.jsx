import { MenuItem, TextField } from '@mui/material';
import { useAppContext } from '../../../src/render';

/**
 * Which track a content belongs to, for the lesson, quiz and assignment forms.
 *
 * Renders nothing on a course without tracks: every content there is on the main path, so
 * the choice would only be noise.
 */
const TrackSelect = ({ tracks = [], value, onChange, disabled = false, sx }) => {
    const { localeMessages } = useAppContext();
    if (tracks.length === 0) {
        return null;
    }
    return (
        <TextField
            select
            id="content-track"
            size="small"
            label={localeMessages['content_track'] || 'Track'}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            disabled={disabled}
            helperText={localeMessages['content_track_help']}
            sx={{ minWidth: 240, ...sx }}
            slotProps={{ select: { displayEmpty: true }, inputLabel: { shrink: true } }}
        >
            <MenuItem value="">{localeMessages['main_path'] || 'Main path'}</MenuItem>
            {tracks.map((track) => (
                <MenuItem key={track.id} value={track.id}>{track.name}</MenuItem>
            ))}
        </TextField>
    );
};

export default TrackSelect;
