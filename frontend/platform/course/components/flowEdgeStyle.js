import { MarkerType } from '@xyflow/react';
import { conditionLabel } from './branching.js';

/** How the flow view draws an edge from `buildFlowGraph`: its colour, dashes and label, by kind. */
export function styleEdge(edge, { theme, localeMessages, trackColors }) {
    const { kind, track, rules, inactive } = edge.data;
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
    // A route out of unpublished content: drawn so the rule stays visible, dotted because no one takes it.
    const inactiveStyle = inactive ? { strokeDasharray: '2 4', opacity: 0.7 } : {};
    return {
        ...edge,
        type: 'smoothstep',
        style: { stroke: color, strokeWidth: 1.5, ...style, ...inactiveStyle },
        markerEnd: { type: MarkerType.ArrowClosed, color },
        ...rest,
    };
}
