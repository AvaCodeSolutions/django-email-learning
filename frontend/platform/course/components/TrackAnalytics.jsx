import { useEffect, useState } from 'react';
import { Alert, Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from '@mui/material';
import { useAppContext } from '../../../src/render.jsx';
import apiClient from '../../../src/apiClient.js';
import { sanitizeEndpointUrl } from '../../../src/sanitizeUrl.js';

/**
 * How learners fared on each track of the course. Renders nothing for a course without tracks,
 * and nothing until the numbers arrive, so a course that does not branch never flashes a
 * placeholder.
 */
const TrackAnalytics = ({ courseId }) => {
    const { localeMessages, analyticsBaseUrl } = useAppContext();
    const base = analyticsBaseUrl?.base ? sanitizeEndpointUrl(analyticsBaseUrl.base) : null;
    const [rows, setRows] = useState(null);
    const [failed, setFailed] = useState(false);

    useEffect(() => {
        if (!base) {
            return;
        }
        apiClient.get(`${base}/track-breakdown/?course_id=${courseId}`)
            .then((data) => setRows(data.data || []))
            .catch((error) => {
                console.error('Error loading track analytics:', error);
                setFailed(true);
            });
    }, [base, courseId]);

    if (failed) {
        return (
            <Alert severity="error" sx={{ mt: 3 }}>
                {localeMessages['track_breakdown_load_failed'] || 'Could not load the track numbers.'}
            </Alert>
        );
    }
    if (!base || !rows || rows.length === 0) {
        return null;
    }

    const title = localeMessages['track_breakdown_title'] || 'Tracks';
    const columns = [
        ['routed', localeMessages['track_routed'] || 'Routed onto it'],
        ['finished', localeMessages['track_finished'] || 'Finished'],
        ['still_on_track', localeMessages['track_still_on'] || 'Still on it'],
        ['left_course', localeMessages['track_left'] || 'Left the course'],
    ];

    return (
        <Box sx={{ mt: 3, py: 3, px: 2, borderRadius: { xs: 0, sm: 2 }, backgroundColor: 'background.box', boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 1px 4px rgba(0,0,0,0.04)' }}>
            <Typography variant="h6" align="center">{title}</Typography>
            {localeMessages['track_breakdown_help'] && (
                <Typography variant="body2" align="center" sx={{ mt: 1, mb: 2, color: 'text.secondary' }}>
                    {localeMessages['track_breakdown_help']}
                </Typography>
            )}
            <TableContainer sx={{ overflowX: 'auto' }}>
                <Table size="small" aria-label={title}>
                    <TableHead>
                        <TableRow>
                            <TableCell>{localeMessages['content_track'] || 'Track'}</TableCell>
                            {columns.map(([key, label]) => (
                                <TableCell key={key} align="right">{label}</TableCell>
                            ))}
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {rows.map((row) => (
                            <TableRow key={row.track_id}>
                                <TableCell component="th" scope="row">{row.name}</TableCell>
                                {columns.map(([key]) => (
                                    <TableCell key={key} align="right" sx={{ fontVariantNumeric: 'tabular-nums' }}>{row[key]}</TableCell>
                                ))}
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>
        </Box>
    );
};

export default TrackAnalytics;
