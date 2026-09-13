import { describe, it, expect } from 'vitest';
import { buildContentTree, conditionLabel, errorMessageFrom } from '../../../platform/course/components/branching.js';

const lesson = (id, title, trackId = null) => ({ id, title, type: 'lesson', track_id: trackId, is_published: true });
const quiz = (id, title, trackId = null) => ({ ...lesson(id, title, trackId), type: 'quiz' });
const rule = (id, sourceId, targetId, condition = 'failed', order = 1, threshold = null) => ({
    id, source_id: sourceId, target_id: targetId, condition, order, threshold,
});

const shape = (rows) => rows.map((row) => (row.kind === 'content'
    ? `content:${row.content.id}@${row.depth}`
    : `${row.kind}${row.track ? `:${row.track.id}` : ''}@${row.depth}`));

describe('buildContentTree', () => {
    it('lays a course without tracks out as a flat list', () => {
        expect(shape(buildContentTree([lesson(1, 'A'), lesson(2, 'B')]))).toEqual(['content:1@0', 'content:2@0']);
    });

    it('places a track directly under the content that routes onto it', () => {
        // Interleaved the way the listing sorts by priority across tracks.
        const contents = [lesson(1, 'Intro'), lesson(10, 'Remedial 1', 7), quiz(2, 'Checkpoint'), lesson(3, 'Wrap up')];
        const tracks = [{ id: 7, name: 'Remedial', parent_track_id: null, merge_into_id: 3 }];

        const rows = buildContentTree(contents, tracks, [rule(1, 2, 7)]);

        expect(shape(rows)).toEqual(['content:1@0', 'content:2@0', 'branch:7@1', 'content:10@1', 'rejoin:7@1', 'content:3@0']);
        expect(rows[1].isBranchPoint).toBe(true);
        expect(rows[2].rules.map((r) => r.condition)).toEqual(['failed']);
        expect(rows[4].mergeContent.title).toBe('Wrap up');
    });

    it('gathers several rules onto one track under a single header, in rule order', () => {
        const contents = [quiz(2, 'Checkpoint'), lesson(10, 'Remedial 1', 7)];
        const tracks = [{ id: 7, name: 'Remedial', parent_track_id: null, merge_into_id: null }];
        const transitions = [rule(2, 2, 7, 'score_lt', 2, 40), rule(1, 2, 7, 'failed', 1)];

        const rows = buildContentTree(contents, tracks, transitions);

        expect(rows.filter((row) => row.kind === 'branch')).toHaveLength(1);
        expect(rows[1].rules.map((r) => r.condition)).toEqual(['failed', 'score_lt']);
        expect(rows[3].mergeContent).toBeNull();
    });

    it('nests a track routed from content on another track', () => {
        const contents = [quiz(2, 'Checkpoint'), quiz(10, 'Remedial check', 7), lesson(20, 'Deep dive', 8)];
        const tracks = [
            { id: 7, name: 'Remedial', parent_track_id: null, merge_into_id: null },
            { id: 8, name: 'Deep', parent_track_id: 7, merge_into_id: 10 },
        ];

        const rows = buildContentTree(contents, tracks, [rule(1, 2, 7), rule(2, 10, 8)]);

        expect(shape(rows)).toEqual([
            'content:2@0', 'branch:7@1', 'content:10@1', 'branch:8@2', 'content:20@2', 'rejoin:8@2', 'rejoin:7@1',
        ]);
    });

    it('shows a shared track once, noting the other content that routes onto it', () => {
        const contents = [quiz(2, 'First check'), quiz(3, 'Second check'), lesson(10, 'Remedial 1', 7)];
        const tracks = [{ id: 7, name: 'Remedial', parent_track_id: null, merge_into_id: null }];

        const rows = buildContentTree(contents, tracks, [rule(1, 2, 7), rule(2, 3, 7)]);

        expect(shape(rows)).toEqual(['content:2@0', 'branch:7@1', 'content:10@1', 'rejoin:7@1', 'content:3@0']);
        expect(rows[1].alsoFrom.map((content) => content.title)).toEqual(['Second check']);
        expect(rows[4].isBranchPoint).toBe(true);
    });

    it('keeps tracks no rule reaches visible, under their own heading', () => {
        const contents = [lesson(1, 'Intro'), lesson(10, 'Orphan lesson', 9)];
        const tracks = [{ id: 9, name: 'Draft', parent_track_id: null, merge_into_id: null }];

        expect(shape(buildContentTree(contents, tracks, []))).toEqual([
            'content:1@0', 'unrouted@0', 'branch:9@1', 'content:10@1', 'rejoin:9@1',
        ]);
    });
});

describe('conditionLabel', () => {
    const localeMessages = { branch_condition_score_gte: 'If score ≥ THRESHOLD', branch_condition_failed: 'If failed' };

    it('fills in the threshold of a score rule', () => {
        expect(conditionLabel({ condition: 'score_gte', threshold: 80 }, localeMessages)).toBe('If score ≥ 80');
    });

    it('uses the plain label for a rule without a threshold', () => {
        expect(conditionLabel({ condition: 'failed', threshold: null }, localeMessages)).toBe('If failed');
    });
});

describe('errorMessageFrom', () => {
    it('joins a list of rule violations', () => {
        expect(errorMessageFrom({ body: { error: ['One.', 'Two.'] } }, 'Fallback')).toBe('One. Two.');
    });

    it('passes a single sentence through', () => {
        expect(errorMessageFrom({ body: { error: 'Content can only be reordered within one track at a time.' } }, 'Fallback'))
            .toBe('Content can only be reordered within one track at a time.');
    });

    it('falls back rather than showing a pydantic error dump', () => {
        expect(errorMessageFrom({ body: { error: '[{"type": "missing"}]' } }, 'Fallback')).toBe('Fallback');
    });

    it('falls back when there is no body', () => {
        expect(errorMessageFrom(new Error('network'), 'Fallback')).toBe('Fallback');
    });
});
