import dagre from '@dagrejs/dagre';
import { trackGroupId } from './flowGraph.js';

export const NODE_WIDTH = 240;
export const NODE_HEIGHT = 72;

// Room around a track's content inside its box; the top leaves space for the track's name.
const GROUP_PADDING = { top: 36, right: 16, bottom: 16, left: 16 };

// The main path is pulled straightest, then each track's own steps; routes and rejoins bend
// around them. Otherwise dagre is free to put a track's content in the main column.
const edgeWeight = (edge) => {
    if (edge.data?.kind !== 'next') {
        return 1;
    }
    return edge.data.track ? 4 : 8;
};

/**
 * Positions for the course map, as React Flow nodes.
 *
 * Laid out top to bottom by dagre with each track as a cluster, so a track's content stays
 * together in a block the main path never runs through. Each track becomes a `track` group node
 * sized around its content, nested inside its parent track's group; content on a track is
 * positioned relative to its group, as React Flow expects of child nodes.
 */
export function layoutFlow(nodes, edges, groups = []) {
    const groupById = new Map(groups.map((group) => [group.id, group]));
    const parentGroupOf = (group) => {
        const parentTrackId = group.track.parent_track_id;
        return parentTrackId != null && groupById.has(trackGroupId(parentTrackId)) ? trackGroupId(parentTrackId) : null;
    };

    // Only tracks holding content, or holding a track that does, get a box.
    const live = new Set();
    for (const node of nodes) {
        let groupId = node.data?.track ? trackGroupId(node.data.track.id) : null;
        while (groupId && groupById.has(groupId) && !live.has(groupId)) {
            live.add(groupId);
            groupId = parentGroupOf(groupById.get(groupId));
        }
    }
    const liveGroups = groups.filter((group) => live.has(group.id));
    const groupOfNode = (node) => {
        const groupId = node.data?.track ? trackGroupId(node.data.track.id) : null;
        return groupId && live.has(groupId) ? groupId : null;
    };

    const graph = new dagre.graphlib.Graph({ compound: true });
    graph.setGraph({ rankdir: 'TB', nodesep: 56, ranksep: 88 });
    graph.setDefaultEdgeLabel(() => ({}));
    for (const group of liveGroups) {
        graph.setNode(group.id, {});
    }
    for (const group of liveGroups) {
        const parentId = parentGroupOf(group);
        if (parentId && live.has(parentId)) {
            graph.setParent(group.id, parentId);
        }
    }
    for (const node of nodes) {
        graph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
        const groupId = groupOfNode(node);
        if (groupId) {
            graph.setParent(node.id, groupId);
        }
    }
    for (const edge of edges) {
        graph.setEdge(edge.source, edge.target, { weight: edgeWeight(edge) });
    }
    dagre.layout(graph);

    const boxes = new Map(nodes.map((node) => {
        const { x, y } = graph.node(node.id);
        return [node.id, { x: x - NODE_WIDTH / 2, y: y - NODE_HEIGHT / 2, width: NODE_WIDTH, height: NODE_HEIGHT }];
    }));

    const depthOf = (group) => {
        let depth = 0;
        const seen = new Set();
        let parentId = parentGroupOf(group);
        while (parentId && live.has(parentId) && !seen.has(parentId)) {
            seen.add(parentId);
            depth += 1;
            parentId = parentGroupOf(groupById.get(parentId));
        }
        return depth;
    };

    // Innermost first, so a track's box can wrap the boxes of the tracks nested in it.
    const groupBoxes = new Map();
    for (const group of [...liveGroups].sort((a, b) => depthOf(b) - depthOf(a))) {
        const members = [
            ...nodes.filter((node) => groupOfNode(node) === group.id).map((node) => boxes.get(node.id)),
            ...liveGroups.filter((child) => parentGroupOf(child) === group.id).map((child) => groupBoxes.get(child.id)),
        ].filter(Boolean);
        const left = Math.min(...members.map((box) => box.x)) - GROUP_PADDING.left;
        const top = Math.min(...members.map((box) => box.y)) - GROUP_PADDING.top;
        const right = Math.max(...members.map((box) => box.x + box.width)) + GROUP_PADDING.right;
        const bottom = Math.max(...members.map((box) => box.y + box.height)) + GROUP_PADDING.bottom;
        groupBoxes.set(group.id, { x: left, y: top, width: right - left, height: bottom - top });
    }

    const placedIn = (box, parentId) => (parentId
        ? { x: box.x - groupBoxes.get(parentId).x, y: box.y - groupBoxes.get(parentId).y }
        : { x: box.x, y: box.y });

    // React Flow needs a parent before its children.
    const groupNodes = [...liveGroups].sort((a, b) => depthOf(a) - depthOf(b)).map((group) => {
        const box = groupBoxes.get(group.id);
        const parentId = parentGroupOf(group);
        return {
            id: group.id,
            type: 'track',
            position: placedIn(box, parentId),
            ...(parentId ? { parentId } : {}),
            width: box.width,
            height: box.height,
            style: { width: box.width, height: box.height },
            zIndex: depthOf(group) - 10,
            selectable: false,
            draggable: false,
            data: { track: group.track, unreached: group.unreached },
        };
    });

    const contentNodes = nodes.map((node) => {
        const parentId = groupOfNode(node);
        return { ...node, position: placedIn(boxes.get(node.id), parentId), ...(parentId ? { parentId } : {}) };
    });

    return [...groupNodes, ...contentNodes];
}
