import { useMemo } from 'react';
import { Box, Chip, Paper, Typography } from '@mui/material';
import AltRouteIcon from '@mui/icons-material/AltRoute';
import AssignmentOutlinedIcon from '@mui/icons-material/AssignmentOutlined';
import BallotOutlinedIcon from '@mui/icons-material/BallotOutlined';
import DescriptionOutlinedIcon from '@mui/icons-material/DescriptionOutlined';
import FlagIcon from '@mui/icons-material/Flag';
import SubdirectoryArrowRightIcon from '@mui/icons-material/SubdirectoryArrowRight';
import { useAppContext } from '../../../src/render.jsx';
import { buildRouteTree, conditionLabel } from './branching.js';

const TYPE_ICONS = { lesson: DescriptionOutlinedIcon, quiz: BallotOutlinedIcon, assignment: AssignmentOutlinedIcon };

const Connector = () => (
    <Box aria-hidden="true" sx={{ width: '2px', height: 14, mx: 'auto', backgroundColor: 'divider' }} />
);

const Marker = ({ icon: Icon, children }) => (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'text.secondary' }}>
        <Icon fontSize="small" />
        <Typography variant="caption">{children}</Typography>
    </Box>
);

const ContentNode = ({ node, onContentClick }) => {
    const { localeMessages } = useAppContext();
    const Icon = TYPE_ICONS[node.content.type] || DescriptionOutlinedIcon;
    const published = node.content.is_published !== false;
    const notPublished = localeMessages['not_published'] || 'Not published';
    return (
        <Paper
            component="button"
            type="button"
            variant="outlined"
            aria-label={published ? node.content.title : `${node.content.title} (${notPublished})`}
            onClick={() => onContentClick?.(node.content.id)}
            sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                width: '100%',
                px: 1.5,
                py: 1,
                textAlign: 'start',
                font: 'inherit',
                cursor: 'pointer',
                backgroundColor: 'background.paper',
                borderStyle: published ? 'solid' : 'dashed',
                borderColor: node.isBranchPoint ? 'primary.main' : 'divider',
                '&:hover, &:focus-visible': { borderColor: 'primary.main' },
            }}
        >
            <Icon fontSize="small" sx={{ color: 'text.secondary', flexShrink: 0 }} />
            <Typography component="span" variant="body2" sx={{ flex: 1, minWidth: 0, overflowWrap: 'anywhere', color: published ? 'text.primary' : 'text.secondary' }}>
                {node.content.title}
            </Typography>
            {!published && <Chip size="small" variant="outlined" label={notPublished} />}
            {node.isBranchPoint && <AltRouteIcon fontSize="small" sx={{ color: 'primary.main', flexShrink: 0 }} />}
        </Paper>
    );
};

const RouteLane = ({ route, onContentClick }) => {
    const { localeMessages } = useAppContext();
    return (
        <Box
            role="group"
            aria-label={route.track.name}
            sx={{
                flex: '1 1 240px',
                minWidth: 220,
                p: 1.5,
                borderRadius: 1,
                backgroundColor: 'action.hover',
                borderInlineStart: (theme) => `3px solid ${theme.palette.primary.main}`,
            }}
        >
            <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 0.75, mb: 1 }}>
                {route.rules.map((rule) => (
                    <Chip key={rule.id} size="small" color="primary" variant="outlined" label={conditionLabel(rule, localeMessages)} />
                ))}
                <Typography component="span" variant="body2" sx={{ fontWeight: 600 }}>{route.track.name}</Typography>
            </Box>
            {route.alsoFrom.length > 0 && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                    {(localeMessages['also_reached_from'] || 'Also reached from: SOURCES').replace('SOURCES', route.alsoFrom.map((content) => content.title).join(', '))}
                </Typography>
            )}
            <Lane nodes={route.nodes} onContentClick={onContentClick} />
            <Box sx={{ mt: 1 }}>
                {route.mergeContent ? (
                    <Marker icon={SubdirectoryArrowRightIcon}>
                        {(localeMessages['rejoins_at'] || 'Rejoins at TITLE').replace('TITLE', route.mergeContent.title)}
                    </Marker>
                ) : (
                    <Marker icon={FlagIcon}>{localeMessages['ends_the_course'] || 'Ends the course'}</Marker>
                )}
            </Box>
        </Box>
    );
};

const Routes = ({ node, onContentClick }) => {
    const { localeMessages } = useAppContext();
    // Without an otherwise rule, a result no rule claims leaves the learner on this path.
    const catchesEverything = node.rules.some((rule) => rule.condition === 'default');
    return (
        <Box sx={{ mt: 1.5 }}>
            <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start', flexWrap: { xs: 'wrap', md: 'nowrap' } }}>
                {node.routes.map((route) => (
                    <RouteLane key={route.track.id} route={route} onContentClick={onContentClick} />
                ))}
            </Box>
            {!catchesEverything && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, textAlign: 'center' }}>
                    {localeMessages['map_no_match'] || 'If no rule matches, the learner continues below.'}
                </Typography>
            )}
        </Box>
    );
};

function Lane({ nodes, onContentClick }) {
    return (
        <Box>
            {nodes.map((node, index) => (
                <Box key={node.content.id}>
                    {index > 0 && <Connector />}
                    <ContentNode node={node} onContentClick={onContentClick} />
                    {node.routes.length > 0 && <Routes node={node} onContentClick={onContentClick} />}
                </Box>
            ))}
        </Box>
    );
}

/**
 * A read-only picture of the course, top to bottom: the main path, and at each branch point
 * the tracks its rules route onto, side by side, each ending where it rejoins. Clicking a node
 * opens it like a row of the content table does.
 */
const CourseMap = ({ contents = [], tracks = [], transitions = [], onContentClick }) => {
    const { localeMessages } = useAppContext();
    const tree = useMemo(() => buildRouteTree(contents, tracks, transitions), [contents, tracks, transitions]);

    return (
        <Box role="region" aria-label={localeMessages['course_view_map'] || 'Map'} sx={{ overflowX: 'auto', px: { xs: 1, md: 2 }, pb: 2 }}>
            <Box sx={{ maxWidth: 1040, mx: 'auto' }}>
                <Lane nodes={tree.spine} onContentClick={onContentClick} />
                {tree.orphans.length > 0 && (
                    <>
                        <Connector />
                        <Lane nodes={tree.orphans} onContentClick={onContentClick} />
                    </>
                )}
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 1.5 }}>
                    <Marker icon={FlagIcon}>{localeMessages['map_course_complete'] || 'Course complete'}</Marker>
                </Box>
                {tree.unrouted.length > 0 && (
                    <Box sx={{ mt: 4 }}>
                        <Typography variant="overline" color="text.secondary">
                            {localeMessages['unrouted_tracks'] || 'Tracks no rule routes onto yet'}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap', alignItems: 'flex-start' }}>
                            {tree.unrouted.map((route) => (
                                <RouteLane key={route.track.id} route={route} onContentClick={onContentClick} />
                            ))}
                        </Box>
                    </Box>
                )}
            </Box>
        </Box>
    );
};

export default CourseMap;
