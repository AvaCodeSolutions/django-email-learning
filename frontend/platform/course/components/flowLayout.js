import { END_NODE_ID, trackGroupId } from './flowGraph.js';

export const NODE_WIDTH = 240;
export const NODE_HEIGHT = 72;

// Room around a track's content inside its box; the top leaves space for the track's name.
const GROUP_PADDING = { top: 36, right: 20, bottom: 20, left: 20 };
// Clear space between neighbouring columns, on top of the padding of every box that opens or
// closes between them - so two track boxes, or a box and the main path, never touch.
const MIN_COLUMN_GAP = 64;
const MIN_ROW_GAP = 72;

/**
 * Positions for the course map, as React Flow nodes.
 *
 * The main path is one straight column on the left. Each track gets a band of columns to the
 * right: its own content in the band's first column, the tracks nested in it packed into the
 * columns after. Bands share a column only when there is at least a free row between them, so
 * a track's box never overlaps another track's box or covers the main path, however the course
 * branches - and the gap between columns grows with nesting, so the padding of nested boxes
 * always fits inside it.
 *
 * Rows come from the edges: every content sits below everything that leads to it, so a track
 * lies between its branch point and the step where it rejoins.
 *
 * Each track becomes a `track` group node sized around its content and nested inside its parent
 * track's group; content on a track is positioned relative to its group, as React Flow expects
 * of child nodes.
 */
export function layoutFlow(nodes, edges, groups = []) {
    const rowOf = rankRows(nodes, edges);

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
    const liveParentOf = (group) => {
        const parentId = parentGroupOf(group);
        return parentId && live.has(parentId) ? parentId : null;
    };
    const groupOfNode = (node) => {
        const groupId = node.data?.track ? trackGroupId(node.data.track.id) : null;
        return groupId && live.has(groupId) ? groupId : null;
    };

    const childrenOf = new Map(liveGroups.map((group) => [group.id, []]));
    const roots = [];
    for (const group of liveGroups) {
        const parentId = liveParentOf(group);
        if (parentId) {
            childrenOf.get(parentId).push(group);
        } else {
            roots.push(group);
        }
    }

    // A band: how many columns a track needs, the rows it spans, and where its children sit in it.
    const bands = new Map();
    const bandOf = (group) => {
        if (bands.has(group.id)) {
            return bands.get(group.id);
        }
        const ownRows = nodes.filter((node) => groupOfNode(node) === group.id).map((node) => rowOf.get(node.id));
        const children = childrenOf.get(group.id).map((child) => ({ id: child.id, ...bandOf(child) }));
        const firstChildColumn = ownRows.length > 0 ? 1 : 0;
        const offsets = packBands(children, firstChildColumn);
        const band = {
            width: Math.max(1, firstChildColumn, ...children.map((child) => offsets.get(child.id) + child.width)),
            top: Math.min(...ownRows, ...children.map((child) => child.top)),
            bottom: Math.max(...ownRows, ...children.map((child) => child.bottom)),
            offsets,
        };
        bands.set(group.id, band);
        return band;
    };
    const rootOffsets = packBands(roots.map((group) => ({ id: group.id, ...bandOf(group) })), 1);

    const columnOfGroup = new Map();
    const assignColumns = (group, column) => {
        columnOfGroup.set(group.id, column);
        const band = bands.get(group.id);
        for (const child of childrenOf.get(group.id)) {
            assignColumns(child, column + band.offsets.get(child.id));
        }
    };
    for (const group of roots) {
        assignColumns(group, rootOffsets.get(group.id));
    }

    const depthOf = (group) => {
        let depth = 0;
        let parentId = liveParentOf(group);
        const seen = new Set();
        while (parentId && !seen.has(parentId)) {
            seen.add(parentId);
            depth += 1;
            parentId = liveParentOf(groupById.get(parentId));
        }
        return depth;
    };
    const nesting = Math.max(0, ...liveGroups.map((group) => depthOf(group) + 1));
    const columnGap = MIN_COLUMN_GAP + (GROUP_PADDING.left + GROUP_PADDING.right) * nesting;
    const rowGap = MIN_ROW_GAP + GROUP_PADDING.top * Math.max(0, nesting - 1);
    const xOf = (column) => column * (NODE_WIDTH + columnGap);
    const yOf = (row) => row * (NODE_HEIGHT + rowGap);

    const boxes = new Map(nodes.map((node) => {
        const groupId = groupOfNode(node);
        const column = groupId ? columnOfGroup.get(groupId) : 0;
        return [node.id, { x: xOf(column), y: yOf(rowOf.get(node.id)), width: NODE_WIDTH, height: NODE_HEIGHT }];
    }));

    // Innermost first, so a track's box can wrap the boxes of the tracks nested in it.
    const groupBoxes = new Map();
    for (const group of [...liveGroups].sort((a, b) => depthOf(b) - depthOf(a))) {
        const members = [
            ...nodes.filter((node) => groupOfNode(node) === group.id).map((node) => boxes.get(node.id)),
            ...childrenOf.get(group.id).map((child) => groupBoxes.get(child.id)),
        ];
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
        const parentId = liveParentOf(group);
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

/** Each node's row: one below the lowest of everything that leads to it. */
function rankRows(nodes, edges) {
    const ids = new Set(nodes.map((node) => node.id));
    const outgoing = new Map(nodes.map((node) => [node.id, []]));
    const indegree = new Map(nodes.map((node) => [node.id, 0]));
    for (const edge of edges) {
        if (ids.has(edge.source) && ids.has(edge.target) && edge.source !== edge.target) {
            outgoing.get(edge.source).push(edge.target);
            indegree.set(edge.target, indegree.get(edge.target) + 1);
        }
    }
    const rows = new Map();
    const queue = nodes.filter((node) => indegree.get(node.id) === 0).map((node) => node.id);
    for (const id of queue) {
        rows.set(id, 0);
    }
    while (queue.length > 0) {
        const id = queue.shift();
        for (const next of outgoing.get(id)) {
            rows.set(next, Math.max(rows.get(next) ?? 0, rows.get(id) + 1));
            indegree.set(next, indegree.get(next) - 1);
            if (indegree.get(next) === 0) {
                queue.push(next);
            }
        }
    }
    // A cycle leaves nodes unranked; put them below everything rather than drop them.
    let lowest = Math.max(0, ...rows.values());
    for (const node of nodes) {
        if (indegree.get(node.id) > 0 && node.id !== END_NODE_ID) {
            lowest += 1;
            rows.set(node.id, lowest);
        }
    }
    if (ids.has(END_NODE_ID)) {
        const others = nodes.filter((node) => node.id !== END_NODE_ID).map((node) => rows.get(node.id));
        rows.set(END_NODE_ID, Math.max(-1, ...others) + 1);
    }
    return rows;
}

/**
 * Left-most column for each band, starting at `startColumn`, sharing a column with an earlier
 * band only when a free row separates them. Returns a map of band id to column offset.
 */
function packBands(bands, startColumn) {
    const placed = [];
    const offsets = new Map();
    const ordered = [...bands].sort((a, b) => a.top - b.top || String(a.id).localeCompare(String(b.id)));
    for (const band of ordered) {
        let column = startColumn;
        const clashes = (other) => column < other.column + other.width
            && other.column < column + band.width
            && band.top - 1 <= other.bottom
            && other.top <= band.bottom + 1;
        while (placed.some(clashes)) {
            column += 1;
        }
        placed.push({ ...band, column });
        offsets.set(band.id, column);
    }
    return offsets;
}
