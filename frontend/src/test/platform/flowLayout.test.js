import { describe, it, expect } from 'vitest';
import { buildFlowGraph } from '../../../platform/course/components/flowGraph.js';
import { layoutFlow } from '../../../platform/course/components/flowLayout.js';

const lesson = (id, title, trackId = null) => ({ id, title, type: 'lesson', track_id: trackId, is_published: true });

describe('layoutFlow', () => {
    it('reads top to bottom, with a track between its branch point and its merge point', () => {
        const contents = [lesson(1, 'Intro'), lesson(10, 'Remedial 1', 7), { ...lesson(2, 'Checkpoint'), type: 'quiz' }, lesson(3, 'Wrap up')];
        const tracks = [{ id: 7, name: 'Remedial', parent_track_id: null, merge_into_id: 3 }];
        const graph = buildFlowGraph(contents, tracks, [{ id: 1, source_id: 2, target_id: 7, condition: 'failed', order: 1, threshold: null }]);

        const positioned = layoutFlow(graph.nodes, graph.edges);
        const y = (id) => positioned.find((node) => node.id === id).position.y;

        expect(positioned.every((node) => Number.isFinite(node.position.x) && Number.isFinite(node.position.y))).toBe(true);
        expect(y('content-1')).toBeLessThan(y('content-2'));
        expect(y('content-2')).toBeLessThan(y('content-10'));
        expect(y('content-10')).toBeLessThan(y('content-3'));
        expect(y('content-3')).toBeLessThan(y('end'));
    });
});
