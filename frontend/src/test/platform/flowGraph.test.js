import { describe, it, expect } from 'vitest';
import { END_NODE_ID, buildFlowGraph } from '../../../platform/course/components/flowGraph.js';

const lesson = (id, title, trackId = null, published = true) => ({ id, title, type: 'lesson', track_id: trackId, is_published: published });
const quiz = (id, title, trackId = null) => ({ ...lesson(id, title, trackId), type: 'quiz' });
const rule = (id, sourceId, targetId, condition = 'failed', order = 1) => ({ id, source_id: sourceId, target_id: targetId, condition, order, threshold: null });

const arrows = (graph) => graph.edges.map((edge) => `${edge.source}>${edge.target}:${edge.data.kind}`);

// Spine: Intro(1), Checkpoint(2), Wrap up(3); Remedial(7) holds lesson 10 and rejoins at Wrap up.
const contents = [lesson(1, 'Intro'), lesson(10, 'Remedial 1', 7), quiz(2, 'Checkpoint'), lesson(3, 'Wrap up')];
const remedial = { id: 7, name: 'Remedial', parent_track_id: null, merge_into_id: 3 };

describe('buildFlowGraph', () => {
    it('chains a course without tracks straight to the end', () => {
        const graph = buildFlowGraph([lesson(1, 'A'), lesson(2, 'B')]);

        expect(graph.nodes.map((node) => node.id)).toEqual(['content-1', 'content-2', END_NODE_ID]);
        expect(arrows(graph)).toEqual(['content-1>content-2:next', `content-2>${END_NODE_ID}:next`]);
    });

    it('draws a route onto a track, the fall-through, and the rejoin', () => {
        const graph = buildFlowGraph(contents, [remedial], [rule(1, 2, 7)]);

        expect(arrows(graph)).toEqual([
            'content-1>content-2:next',
            'content-10>content-3:rejoin',
            'content-2>content-10:route',
            'content-2>content-3:otherwise',
            `content-3>${END_NODE_ID}:next`,
        ]);
        const route = graph.edges.find((edge) => edge.data.kind === 'route');
        expect(route.data.rules.map((r) => r.condition)).toEqual(['failed']);
        expect(route.data.track.name).toBe('Remedial');
        expect(route.data.inactive).toBe(false);
    });

    it('marks the routes out of unpublished content inactive, and its next step as the path taken', () => {
        const draftCheckpoint = { ...quiz(2, 'Checkpoint'), is_published: false };
        const graph = buildFlowGraph([lesson(1, 'Intro'), lesson(10, 'Remedial 1', 7), draftCheckpoint, lesson(3, 'Wrap up')], [remedial], [rule(1, 2, 7)]);

        expect(arrows(graph)).toEqual([
            'content-1>content-2:next',
            'content-10>content-3:rejoin',
            'content-2>content-3:next',
            'content-2>content-10:route',
            `content-3>${END_NODE_ID}:next`,
        ]);
        expect(graph.edges.find((edge) => edge.data.kind === 'route').data.inactive).toBe(true);
    });

    it('marks the fall-through behind an otherwise rule as taken only without a result', () => {
        const advanced = { id: 8, name: 'Advanced', parent_track_id: null, merge_into_id: 3 };
        const graph = buildFlowGraph(contents, [remedial, advanced], [rule(1, 2, 7), rule(2, 2, 8, 'default', 2)]);

        expect(graph.edges.find((edge) => edge.id === 'content-2-fallthrough').data.kind).toBe('unsubmitted');
    });

    it('sends a route onto an empty track straight to where it rejoins', () => {
        const empty = { id: 9, name: 'Empty', parent_track_id: null, merge_into_id: 3 };
        const graph = buildFlowGraph(contents, [remedial, empty], [rule(1, 2, 9)]);

        expect(graph.edges.find((edge) => edge.id === 'content-2-route-9').target).toBe('content-3');
    });

    it('ends the course from a track with no merge point', () => {
        const terminal = { ...remedial, merge_into_id: null };
        const graph = buildFlowGraph(contents, [terminal], [rule(1, 2, 7)]);

        expect(graph.edges.find((edge) => edge.id === 'content-10-next')).toMatchObject({ target: END_NODE_ID, data: { kind: 'ends' } });
    });

    it('climbs to the parent track for a nested track without its own merge point', () => {
        const nested = { id: 11, name: 'Deep', parent_track_id: 7, merge_into_id: null };
        const withNested = [...contents, quiz(10, 'Remedial check', 7), lesson(20, 'Deep dive', 11)].filter(
            (content, index, all) => all.findIndex((other) => other.id === content.id) === index,
        );
        const graph = buildFlowGraph(withNested, [remedial, nested], [rule(1, 2, 7), rule(2, 10, 11)]);

        expect(graph.edges.find((edge) => edge.id === 'content-20-next')).toMatchObject({ target: 'content-3', data: { kind: 'rejoin' } });
    });

    it('flags content on a track no rule routes onto', () => {
        const graph = buildFlowGraph(contents, [remedial], []);

        expect(graph.nodes.find((node) => node.id === 'content-10').data.unreached).toBe(true);
        expect(graph.nodes.find((node) => node.id === 'content-1').data.unreached).toBe(false);
    });

    it('keeps unpublished content in the picture', () => {
        const graph = buildFlowGraph([lesson(1, 'A'), lesson(2, 'Draft', null, false), lesson(3, 'C')]);

        expect(arrows(graph)).toEqual(['content-1>content-2:next', 'content-2>content-3:next', `content-3>${END_NODE_ID}:next`]);
    });

    it('describes each track as a group, noting the ones no rule reaches', () => {
        const draft = { id: 9, name: 'Draft', parent_track_id: null, merge_into_id: null };
        const graph = buildFlowGraph(contents, [remedial, draft], [rule(1, 2, 7)]);

        expect(graph.groups.map((group) => [group.id, group.unreached])).toEqual([['track-7', false], ['track-9', true]]);
    });
});
