import { Box, InputLabel, MenuItem, Select, Typography } from '@mui/material';
import { useAppContext } from '../../../src/render';

/**
 * Which track a content belongs to, for the lesson, quiz and assignment forms.
 *
 * Laid out like the other settings on those forms - a label above the control and the
 * explanation below it. Renders nothing on a course without tracks: every content there is on
 * the main path, so the choice would only be noise.
 */
const TrackSelect = ({ tracks = [], value, onChange, disabled = false, fullWidth = false, sx }) => {
    const { localeMessages } = useAppContext();
    if (tracks.length === 0) {
        return null;
    }
    return (
        <Box sx={sx}>
            <InputLabel id="content-track-label" sx={{ mb: 1, fontSize: '0.9rem', color: 'text.secondary' }}>
                {localeMessages['content_track'] || 'Track'}
            </InputLabel>
            <Select
                size="small"
                labelId="content-track-label"
                value={value}
                onChange={(event) => onChange(event.target.value)}
                disabled={disabled}
                displayEmpty
                sx={fullWidth ? { width: '100%' } : { minWidth: 240 }}
            >
                <MenuItem value="">{localeMessages['main_path'] || 'Main path'}</MenuItem>
                {tracks.map((track) => (
                    <MenuItem key={track.id} value={track.id}>{track.name}</MenuItem>
                ))}
            </Select>
            {localeMessages['content_track_help'] && (
                <Typography variant="caption" sx={{ display: 'block', color: 'text.secondary', mt: 0.5 }}>
                    {localeMessages['content_track_help']}
                </Typography>
            )}
        </Box>
    );
};

export default TrackSelect;
