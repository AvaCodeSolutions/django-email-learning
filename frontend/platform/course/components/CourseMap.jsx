import { useEffect, useMemo, useRef } from 'react';
import { Background, Controls, Handle, MarkerType, Position, ReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Box, Chip, Typography } from '@mui/material';
import { alpha, useTheme } from '@mui/material/styles';
import AltRouteIcon from '@mui/icons-material/AltRoute';
import AssignmentOutlinedIcon from '@mui/icons-material/AssignmentOutlined';
import BallotOutlinedIcon from '@mui/icons-material/BallotOutlined';
import DescriptionOutlinedIcon from '@mui/icons-material/DescriptionOutlined';
import FlagIcon from '@mui/icons-material/Flag';
import { useAppContext } from '../../../src/render.jsx';
import { conditionLabel } from './branching.js';
import { buildFlowGraph } from './flowGraph.js';
import { NODE_HEIGHT, NODE_WIDTH, layoutFlow } from './flowLayout.js';

const TYPE_ICONS = { lesson: DescriptionOutlinedIcon, quiz: BallotOutlinedIcon, assignment: AssignmentOutlinedIcon };

// Tracks are told apart by colour; each track's box also carries its name, so the palette can repeat.
const TRACK_COLORS = ['#7e57c2', '#00897b', '#ef6c00', '#1e88e5', '#d81b60', '#6d4c41'];

const HIDDEN_HANDLE = { opacity: 0, pointerEvents: 'none' };

function ContentNode({ data }) {
    const { localeMessages } = useAppContext();
    const Icon = TYPE_ICONS[data.content.type] || DescriptionOutlinedIcon;
    const published = data.content.is_published !== false;
    const notPublished = localeMessages['not_published'] || 'Not published';
    return (
        <Box
            role="button"
            tabIndex={0}
            aria-label={published ? data.content.title : `${data.content.title} (${notPublished})`}
            onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    data.onOpen?.();
                }
            }}
            sx={(theme) => ({
                width: NODE_WIDTH,
                minHeight: NODE_HEIGHT,
                boxSizing: 'border-box',
                px: 1.5,
                py: 1,
                borderRadius: 1,
                cursor: 'pointer',
                backgroundColor: 'background.paper',
                border: '1px solid',
                borderStyle: published ? 'solid' : 'dashed',
                borderColor: data.isBranchPoint ? 'primary.main' : 'divider',
                borderInlineStartWidth: 4,
                borderInlineStartStyle: 'solid',
                borderInlineStartColor: data.color ?? theme.palette.text.disabled,
                '&:hover, &:focus-visible': { borderColor: 'primary.main', outline: 'none' },
            })}
        >
            <Handle type="target" position={Position.Top} isConnectable={false} style={HIDDEN_HANDLE} />
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 0.75 }}>
                <Icon fontSize="small" sx={{ color: 'text.secondary', mt: '1px', flexShrink: 0 }} />
                <Typography
                    component="span"
                    variant="body2"
                    sx={{ flex: 1, minWidth: 0, fontWeight: 500, color: published ? 'text.primary' : 'text.secondary', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}
                >
                    {data.content.title}
                </Typography>
                {data.isBranchPoint && <AltRouteIcon fontSize="small" sx={{ color: 'primary.main', flexShrink: 0 }} />}
            </Box>
            {!published && (
                <Box sx={{ mt: 0.5 }}>
                    <Chip size="small" variant="outlined" label={notPublished} sx={{ height: 18, fontSize: '0.65rem' }} />
                </Box>
            )}
            <Handle type="source" position={Position.Bottom} isConnectable={false} style={HIDDEN_HANDLE} />
        </Box>
    );
}

function EndNode() {
    const { localeMessages } = useAppContext();
    return (
        <Box
            sx={{
                width: NODE_WIDTH,
                minHeight: 44,
                boxSizing: 'border-box',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 0.75,
                borderRadius: 5,
                border: '1px solid',
                borderColor: 'divider',
                backgroundColor: 'action.hover',
                color: 'text.secondary',
            }}
        >
            <Handle type="target" position={Position.Top} isConnectable={false} style={HIDDEN_HANDLE} />
            <FlagIcon fontSize="small" />
            <Typography variant="body2">{localeMessages['map_course_complete'] || 'Course complete'}</Typography>
        </Box>
    );
}

function TrackGroupNode({ data }) {
    const { localeMessages } = useAppContext();
    return (
        <Box
            sx={(theme) => ({
                width: '100%',
                height: '100%',
                boxSizing: 'border-box',
                borderRadius: 2,
                border: `1.5px dashed ${data.color}`,
                backgroundColor: alpha(data.color, theme.palette.mode === 'dark' ? 0.14 : 0.07),
                px: 1.25,
                py: 0.75,
                pointerEvents: 'none',
            })}
        >
            <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 0.5 }}>
                <AltRouteIcon sx={{ fontSize: 16, color: data.color }} />
                <Typography variant="caption" sx={{ fontWeight: 700, color: data.color }}>{data.track.name}</Typography>
                {data.unreached && (
                    <Chip size="small" color="warning" variant="outlined" label={localeMessages['map_unreached'] || 'No rule routes here'} sx={{ height: 18, fontSize: '0.65rem' }} />
                )}
            </Box>
        </Box>
    );
}

const NODE_TYPES = { content: ContentNode, end: EndNode, track: TrackGroupNode };

function styleEdge(edge, { theme, localeMessages, trackColors }) {
    const { kind, track, rules } = edge.data;
    const neutral = theme.palette.text.secondary;
    const trackColor = track ? trackColors.get(track.id) ?? neutral : neutral;
    const labelled = (label, color) => ({
        label,
        labelStyle: { fill: color, fontWeight: 600, fontSize: 12 },
        labelBgStyle: { fill: theme.palette.background.paper },
        labelBgPadding: [6, 3],
        labelBgBorderRadius: 4,
    });

    const byKind = {
        route: {
            color: trackColor,
            style: { strokeWidth: 2 },
            ...labelled((rules || []).map((rule) => conditionLabel(rule, localeMessages)).join(' · '), trackColor),
        },
        otherwise: { color: neutral, ...labelled(localeMessages['map_otherwise'] || 'Otherwise', neutral) },
        unsubmitted: {
            color: theme.palette.text.disabled,
            style: { strokeDasharray: '6 4' },
            ...labelled(localeMessages['map_not_submitted'] || 'If not submitted', theme.palette.text.disabled),
        },
        rejoin: { color: trackColor, style: { strokeDasharray: '6 4' } },
        ends: { color: trackColor, style: { strokeDasharray: '6 4' } },
        next: { color: trackColor },
    };
    const { color, style = {}, ...rest } = byKind[kind] || byKind.next;
    return {
        ...edge,
        type: 'smoothstep',
        style: { stroke: color, strokeWidth: 1.5, ...style },
        markerEnd: { type: MarkerType.ArrowClosed, color },
        ...rest,
    };
}

/**
 * A read-only map of the course: every content as a node and every move a learner can make as
 * an arrow - down the path, onto a track a rule selects, and back to where a track rejoins. Each
 * track is a box around its content, so anything outside every box is on the main path.
 * Clicking a node opens the content, as a row of the content table does.
 */
const CourseMap = ({ contents = [], tracks = [], transitions = [], onContentClick }) => {
    const { localeMessages } = useAppContext();
    const theme = useTheme();
    // Read through a ref so a new callback from the parent does not lay the graph out again.
    const openRef = useRef(onContentClick);
    useEffect(() => {
        openRef.current = onContentClick;
    });

    const { nodes, edges } = useMemo(() => {
        const trackColors = new Map(tracks.map((track, index) => [track.id, TRACK_COLORS[index % TRACK_COLORS.length]]));
        const graph = buildFlowGraph(contents, tracks, transitions);
        const positioned = layoutFlow(graph.nodes, graph.edges, graph.groups).map((node) => {
            if (node.type === 'track') {
                return { ...node, data: { ...node.data, color: trackColors.get(node.data.track.id) } };
            }
            if (node.type === 'content') {
                return {
                    ...node,
                    data: {
                        ...node.data,
                        color: node.data.track ? trackColors.get(node.data.track.id) : null,
                        onOpen: () => openRef.current?.(node.data.content.id),
                    },
                };
            }
            return node;
        });
        return {
            nodes: positioned,
            edges: graph.edges.map((edge) => styleEdge(edge, { theme, localeMessages, trackColors })),
        };
    }, [contents, tracks, transitions, theme, localeMessages]);

    return (
        <Box
            role="region"
            aria-label={localeMessages['course_view_map'] || 'Map'}
            sx={{ height: { xs: 480, md: 640 }, mx: { xs: 0, md: 1 }, border: '1px solid', borderColor: 'divider', borderRadius: { xs: 0, sm: 2 }, overflow: 'hidden' }}
        >
            <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={NODE_TYPES}
                colorMode={theme.palette.mode}
                fitView
                fitViewOptions={{ padding: 0.15 }}
                minZoom={0.2}
                nodesDraggable={false}
                nodesConnectable={false}
                nodesFocusable={false}
                edgesFocusable={false}
                elementsSelectable={false}
                onNodeClick={(_, node) => {
                    if (node.type === 'content') {
                        openRef.current?.(node.data.content.id);
                    }
                }}
            >
                <Background gap={20} />
                <Controls showInteractive={false} />
            </ReactFlow>
        </Box>
    );
};

export default CourseMap;
