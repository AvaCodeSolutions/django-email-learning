import { Box, Chip, Typography } from '@mui/material';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutlined';
import RemoveCircleOutlineIcon from '@mui/icons-material/RemoveCircleOutlined';
import ScheduleIcon from '@mui/icons-material/Schedule';
import { useAppContext } from '../../../src/render.jsx';

const STATUS_ICONS = { delivered: CheckCircleOutlineIcon, scheduled: ScheduleIcon, not_sent: RemoveCircleOutlineIcon };

/**
 * The route one learner has taken through a branching course: every content they were sent or
 * are scheduled to receive, in order, grouped by the track each part was on.
 */
function LearnerPath({ path = [] }) {
    const { localeMessages } = useAppContext();
    if (path.length === 0) {
        return null;
    }

    const segments = [];
    for (const step of path) {
        const trackId = step.track_id ?? null;
        const last = segments[segments.length - 1];
        if (last && last.trackId === trackId) {
            last.steps.push(step);
        } else {
            segments.push({
                trackId,
                label: trackId === null ? (localeMessages['main_path'] || 'Main path') : step.track_name,
                steps: [step],
            });
        }
    }
    const statusLabel = (status) => localeMessages[`path_status_${status}`] || status;

    return (
        <Box sx={{ px: 3, py: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>{localeMessages['learner_path'] || 'Path taken'}</Typography>
            {segments.map((segment, index) => (
                <Box
                    key={index}
                    role="group"
                    aria-label={segment.label}
                    sx={{
                        mb: 1,
                        paddingInlineStart: segment.trackId === null ? 0 : 1.5,
                        borderInlineStart: (theme) => (segment.trackId === null ? 'none' : `3px solid ${theme.palette.primary.light}`),
                    }}
                >
                    <Typography variant="caption" color="text.secondary">{segment.label}</Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75, mt: 0.5 }}>
                        {segment.steps.map((step) => {
                            const Icon = STATUS_ICONS[step.status] || RemoveCircleOutlineIcon;
                            return (
                                <Chip
                                    key={step.course_content_id}
                                    size="small"
                                    icon={<Icon />}
                                    label={step.title}
                                    variant={step.status === 'delivered' ? 'filled' : 'outlined'}
                                    aria-label={`${step.title}: ${statusLabel(step.status)}`}
                                />
                            );
                        })}
                    </Box>
                </Box>
            ))}
        </Box>
    );
}

export default LearnerPath;
