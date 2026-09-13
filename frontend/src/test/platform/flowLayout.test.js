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

    it('never overlaps two track boxes, even when tracks only add content and rejoin at the next step', () => {
        // Spine: Intro(1), Checkpoint(2), Wrap up(3), Review(4), Final(5).
        // Checkpoint routes onto A (three lessons) and B (one lesson), both rejoining at Wrap up - the
        // very next main-path content, so nothing is skipped. Review routes onto C, rejoining at Final.
        // D is nested in A, routed from A's first lesson and rejoining at A's second.
        const spine = [lesson(1, 'Intro'), quiz(2, 'Checkpoint'), lesson(3, 'Wrap up'), quiz(4, 'Review'), lesson(5, 'Final')];
        const onTracks = [
            quiz(10, 'A1', 7), lesson(11, 'A2', 7), lesson(12, 'A3', 7),
            lesson(13, 'B1', 8),
            lesson(14, 'C1', 9), lesson(15, 'C2', 9),
            lesson(17, 'D1', 16),
        ];
        const tracks = [
            { id: 7, name: 'A', parent_track_id: null, merge_into_id: 3 },
            { id: 8, name: 'B', parent_track_id: null, merge_into_id: 3 },
            { id: 9, name: 'C', parent_track_id: null, merge_into_id: 5 },
            { id: 16, name: 'D', parent_track_id: 7, merge_into_id: 11 },
        ];
        const nodes = layout([...spine, ...onTracks], tracks, [rule(1, 2, 7), rule(2, 2, 8), rule(3, 4, 9), rule(4, 10, 16)]);

        const groups = nodes.filter((node) => node.type === 'track');
        const ancestry = (node) => {
            const chain = [];
            let current = node;
            while (current.parentId) {
                chain.push(current.parentId);
                current = nodes.find((candidate) => candidate.id === current.parentId);
            }
            return chain;
        };
        for (const a of groups) {
            for (const b of groups) {
                if (a.id >= b.id || ancestry(a).includes(b.id) || ancestry(b).includes(a.id)) {
                    continue;
                }
                expect(overlaps(boxOf(nodes, a.id), boxOf(nodes, b.id)), `${a.id} overlaps ${b.id}`).toBe(false);
            }
        }
        for (const id of ['content-1', 'content-2', 'content-3', 'content-4', 'content-5', 'end']) {
            for (const group of groups) {
                expect(overlaps(boxOf(nodes, id), boxOf(nodes, group.id)), `${id} is inside ${group.id}`).toBe(false);
            }
        }
    });

    it('keeps the main path in one straight column, clear of every track', () => {
        const nodes = layout(contents, [remedial], [rule(1, 2, 7)]);
        const spineX = ['content-1', 'content-2', 'content-4', 'content-3', 'end'].map((id) => boxOf(nodes, id).x);

        expect(new Set(spineX).size).toBe(1);
        expect(boxOf(nodes, 'track-7').x).toBeGreaterThan(spineX[0] + NODE_WIDTH);
    });

    it('lets a later track reuse a column once an earlier track has rejoined', () => {
        // Spine: 1, Checkpoint(2), 3, Review(4), 5. A (10, 11) branches at 2 and rejoins at 3;
        // C (14) branches at 4 and rejoins at 5, well below where A ends.
        const nodes = layout(
            [lesson(1, 'Intro'), quiz(2, 'Checkpoint'), lesson(3, 'Wrap up'), quiz(4, 'Review'), lesson(5, 'Final'), lesson(10, 'A1', 7), lesson(11, 'A2', 7), lesson(14, 'C1', 9)],
            [{ id: 7, name: 'A', parent_track_id: null, merge_into_id: 3 }, { id: 9, name: 'C', parent_track_id: null, merge_into_id: 5 }],
            [rule(1, 2, 7), rule(2, 4, 9)],
        );

        expect(boxOf(nodes, 'track-9').x).toBe(boxOf(nodes, 'track-7').x);
        expect(overlaps(boxOf(nodes, 'track-7'), boxOf(nodes, 'track-9'))).toBe(false);
    });

    it('puts tracks from the same branch point side by side, with room between their boxes', () => {
        const nodes = layout(
            [lesson(1, 'Intro'), quiz(2, 'Checkpoint'), lesson(3, 'Wrap up'), lesson(10, 'A1', 7), lesson(11, 'A2', 7), lesson(13, 'B1', 8)],
            [{ id: 7, name: 'A', parent_track_id: null, merge_into_id: 3 }, { id: 8, name: 'B', parent_track_id: null, merge_into_id: 3 }],
            [rule(1, 2, 7), rule(2, 2, 8)],
        );
        const [left, right] = [boxOf(nodes, 'track-7'), boxOf(nodes, 'track-8')].sort((a, b) => a.x - b.x);

        expect(right.x - (left.x + left.width)).toBeGreaterThanOrEqual(48);
    });
});
