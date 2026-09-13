/**
 * Course branching, as the authoring UI sees it.
 *
 * The contents listing returns three flat lists - contents, tracks and routing rules.
 * `buildContentTree` turns them into the rows the content table renders: each track sits
 * directly under the content that routes onto it, framed by a header naming the rule and a
 * footer naming where the learner rejoins.
 */

export const TRANSITION_CONDITIONS = ['passed', 'failed', 'score_gte', 'score_lt', 'default'];
export const THRESHOLD_CONDITIONS = new Set(['score_gte', 'score_lt']);

export function conditionLabel(rule, localeMessages) {
    const template = localeMessages[`branch_condition_${rule.condition}`] || rule.condition;
    return THRESHOLD_CONDITIONS.has(rule.condition)
        ? template.replace('THRESHOLD', String(rule.threshold))
        : template;
}

/**
 * A message fit to show an author, from a failed apiClient call.
 *
 * Model rule violations arrive as a sentence or a list of sentences. A pydantic error body is
 * a JSON dump written for developers, so it falls back like any other failure.
 */
export function errorMessageFrom(error, fallback) {
    const body = error?.body?.error;
    if (Array.isArray(body) && body.length > 0) {
        return body.join(' ');
    }
    if (typeof body === 'string' && body.trim() !== '' && !body.trim().startsWith('[')) {
        return body;
    }
    return fallback;
}

/**
 * The rows of the content table, in display order.
 *
 * - `{ kind: 'content', content, depth, isBranchPoint }`
 * - `{ kind: 'branch', track, rules, alsoFrom, depth }` - opens a track; `rules` are the ones on
 *   the content above that route here, `alsoFrom` the other contents that route here too
 * - `{ kind: 'rejoin', track, mergeContent, depth }` - closes it; `mergeContent` is null when
 *   the track ends the course
 * - `{ kind: 'unrouted', depth }` - heads the tracks no rule reaches, so they stay editable
 *
 * A track appears once, under the first content that routes onto it. Contents keep the order
 * of the list passed in, which is what lets a drag show its new position before it is saved.
 */
export function buildContentTree(contents, tracks = [], transitions = []) {
    const contentsByTrack = new Map();
    for (const content of contents) {
        const trackId = content.track_id ?? null;
        if (!contentsByTrack.has(trackId)) {
            contentsByTrack.set(trackId, []);
        }
        contentsByTrack.get(trackId).push(content);
    }
    const contentById = new Map(contents.map((content) => [content.id, content]));
    const trackById = new Map(tracks.map((track) => [track.id, track]));

    const rulesBySource = new Map();
    const sourcesByTarget = new Map();
    for (const rule of [...transitions].sort((a, b) => a.order - b.order)) {
        if (!rulesBySource.has(rule.source_id)) {
            rulesBySource.set(rule.source_id, []);
        }
        rulesBySource.get(rule.source_id).push(rule);
        if (!sourcesByTarget.has(rule.target_id)) {
            sourcesByTarget.set(rule.target_id, new Set());
        }
        sourcesByTarget.get(rule.target_id).add(rule.source_id);
    }

    const rows = [];
    const placed = new Set();

    const placeTrack = (track, rules, sourceId, depth) => {
        placed.add(track.id);
        const alsoFrom = [...(sourcesByTarget.get(track.id) || [])]
            .filter((id) => id !== sourceId)
            .map((id) => contentById.get(id))
            .filter(Boolean);
        rows.push({ kind: 'branch', key: `branch-${track.id}`, track, rules, alsoFrom, depth });
        walk(track.id, depth);
        rows.push({
            kind: 'rejoin',
            key: `rejoin-${track.id}`,
            track,
            mergeContent: track.merge_into_id != null ? contentById.get(track.merge_into_id) ?? null : null,
            depth,
        });
    };

    function walk(trackId, depth) {
        for (const content of contentsByTrack.get(trackId) || []) {
            const rules = rulesBySource.get(content.id) || [];
            rows.push({ kind: 'content', key: `content-${content.id}`, content, depth, isBranchPoint: rules.length > 0 });
            const targets = [];
            for (const rule of rules) {
                if (!targets.includes(rule.target_id)) {
                    targets.push(rule.target_id);
                }
            }
            for (const targetId of targets) {
                const track = trackById.get(targetId);
                if (track && !placed.has(targetId)) {
                    placeTrack(track, rules.filter((rule) => rule.target_id === targetId), content.id, depth + 1);
                }
            }
        }
    }

    walk(null, 0);

    const unrouted = tracks.filter((track) => !placed.has(track.id)).sort((a, b) => a.id - b.id);
    if (unrouted.length > 0) {
        rows.push({ kind: 'unrouted', key: 'unrouted', depth: 0 });
        for (const track of unrouted) {
            if (!placed.has(track.id)) {
                placeTrack(track, [], null, 1);
            }
        }
    }

    // Content on a track the listing did not return would otherwise vanish from the table.
    for (const trackId of contentsByTrack.keys()) {
        if (trackId !== null && !trackById.has(trackId)) {
            walk(trackId, 0);
        }
    }
    return rows;
}
