import { describe, it, expect } from 'vitest';
import { buildFlowGraph } from '../../../platform/course/components/flowGraph.js';
import { NODE_HEIGHT, NODE_WIDTH, layoutFlow } from '../../../platform/course/components/flowLayout.js';

const lesson = (id, title, trackId = null) => ({ id, title, type: 'lesson', track_id: trackId, is_published: true });
const quiz = (id, title, trackId = null) => ({ ...lesson(id, title, trackId), type: 'quiz' });
const rule = (id, sourceId, targetId) => ({ id, source_id: sourceId, target_id: targetId, condition: 'failed', order: 1, threshold: null });

// Child positions are relative to their group, so walk up to get a node's place on the map.
const boxOf = (nodes, id) => {
    let node = nodes.find((candidate) => candidate.id === id);
    const width = node.width ?? NODE_WIDTH;
    const height = node.height ?? NODE_HEIGHT;
    let { x, y } = node.position;
    while (node.parentId) {
        node = nodes.find((candidate) => candidate.id === node.parentId);
        x += node.position.x;
        y += node.position.y;
    }
    return { x, y, width, height };
};
const overlaps = (a, b) => a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;

function layout(contents, tracks, transitions) {
    const graph = buildFlowGraph(contents, tracks, transitions);
    return layoutFlow(graph.nodes, graph.edges, graph.groups);
}

// Spine: Intro(1), Checkpoint(2), Practice(4), Wrap up(3); Remedial(7) holds 10 and 11 and rejoins at Wrap up.
const contents = [
    lesson(1, 'Intro'), lesson(10, 'Remedial 1', 7), quiz(2, 'Checkpoint'), lesson(11, 'Remedial 2', 7), lesson(4, 'Practice'), lesson(3, 'Wrap up'),
];
const remedial = { id: 7, name: 'Remedial', parent_track_id: null, merge_into_id: 3 };

describe('layoutFlow', () => {
    it('reads top to bottom, with a track between its branch point and its merge point', () => {
        const nodes = layout(contents, [remedial], [rule(1, 2, 7)]);
        const y = (id) => boxOf(nodes, id).y;

        expect(y('content-1')).toBeLessThan(y('content-2'));
        expect(y('content-2')).toBeLessThan(y('content-10'));
        expect(y('content-10')).toBeLessThan(y('content-11'));
        expect(y('content-11')).toBeLessThan(y('content-3'));
        expect(y('content-3')).toBeLessThan(y('end'));
    });

    it('boxes a track around its content, and the main path stays outside the box', () => {
        const nodes = layout(contents, [remedial], [rule(1, 2, 7)]);
        const group = nodes.find((node) => node.id === 'track-7');

        expect(group.type).toBe('track');
        expect(nodes.indexOf(group)).toBeLessThan(nodes.findIndex((node) => node.id === 'content-10'));
        for (const id of ['content-10', 'content-11']) {
            const child = nodes.find((node) => node.id === id);
            expect(child.parentId).toBe('track-7');
            expect(child.position.x).toBeGreaterThanOrEqual(0);
            expect(child.position.y).toBeGreaterThanOrEqual(0);
            expect(child.position.x + NODE_WIDTH).toBeLessThanOrEqual(group.width);
            expect(child.position.y + NODE_HEIGHT).toBeLessThanOrEqual(group.height);
        }
        const groupBox = boxOf(nodes, 'track-7');
        for (const id of ['content-1', 'content-2', 'content-4', 'content-3']) {
            expect(nodes.find((node) => node.id === id).parentId).toBeUndefined();
            expect(overlaps(boxOf(nodes, id), groupBox)).toBe(false);
        }
    });

    it('nests a track inside the box of the track it branches off', () => {
        const deep = { id: 12, name: 'Deep', parent_track_id: 7, merge_into_id: null };
        const nodes = layout(
            [...contents, lesson(20, 'Deep dive', 12)],
            [remedial, deep],
            [rule(1, 2, 7), rule(2, 11, 12)],
        );

        expect(nodes.find((node) => node.id === 'track-12').parentId).toBe('track-7');
        expect(nodes.find((node) => node.id === 'content-20').parentId).toBe('track-12');
        expect(nodes.findIndex((node) => node.id === 'track-7')).toBeLessThan(nodes.findIndex((node) => node.id === 'track-12'));
    });

    it('draws no box for a track with nothing on it', () => {
        const empty = { id: 9, name: 'Empty', parent_track_id: null, merge_into_id: 3 };
        const nodes = layout(contents, [remedial, empty], [rule(1, 2, 7), rule(2, 2, 9)]);

        expect(nodes.find((node) => node.id === 'track-9')).toBeUndefined();
    });
});
