/**
 * Course branching, as the authoring UI sees it.
 *
 * The contents listing returns three flat lists - contents, tracks and routing rules.
 * `buildRouteTree` nests them: each track under the content that routes onto it. The course
 * map draws that tree directly; `buildContentTree` flattens it into the rows of the content
 * table, so both views always agree on where a track sits.
 */

export const TRANSITION_CONDITIONS = ['passed', 'failed', 'score_gte', 'score_lt', 'default'];
export const DECISION_TRANSITION_CONDITIONS = ['option_selected', 'default'];
export const THRESHOLD_CONDITIONS = new Set(['score_gte', 'score_lt']);
export const OPTION_CONDITIONS = new Set(['option_selected']);

export function conditionLabel(rule, localeMessages) {
    const template = localeMessages[`branch_condition_${rule.condition}`] || rule.condition;
    if (THRESHOLD_CONDITIONS.has(rule.condition)) {
        return template.replace('THRESHOLD', String(rule.threshold));
    }
    if (OPTION_CONDITIONS.has(rule.condition)) {
        // A replacer function, so an answer containing `$&` is shown as written.
        return template.replace('OPTION', () => rule.option_text ?? '');
    }
    return template;
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
 * The course as a tree of routes.
 *
 * - `spine` - the main path's contents, each `{ content, isBranchPoint, rules, routes }`
 * - a route is `{ track, rules, alsoFrom, nodes, mergeContent }`: `rules` are the ones on the
 *   content above that route here, `alsoFrom` the other contents that route here too, `nodes`
 *   the track's contents, `mergeContent` where it rejoins (null when it ends the course)
 * - `unrouted` - routes for tracks no rule reaches, so they stay visible and editable
 * - `orphans` - contents on a track the listing did not return, rather than dropping them
 *
 * A track appears once, under the first content that routes onto it. Contents keep the order
 * of the list passed in, which is what lets a drag show its new position before it is saved.
 */
export function buildRouteTree(contents, tracks = [], transitions = []) {
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

    const placed = new Set();

    const routeFor = (track, rules, sourceId) => {
        placed.add(track.id);
        return {
            track,
            rules,
            alsoFrom: [...(sourcesByTarget.get(track.id) || [])]
                .filter((id) => id !== sourceId)
                .map((id) => contentById.get(id))
                .filter(Boolean),
            nodes: nodesOn(track.id),
            mergeContent: track.merge_into_id != null ? contentById.get(track.merge_into_id) ?? null : null,
        };
    };

    function nodesOn(trackId) {
        return (contentsByTrack.get(trackId) || []).map((content) => {
            const rules = rulesBySource.get(content.id) || [];
            const routes = [];
            const targets = [];
            for (const rule of rules) {
                if (!targets.includes(rule.target_id)) {
                    targets.push(rule.target_id);
                }
            }
            for (const targetId of targets) {
                const track = trackById.get(targetId);
                if (track && !placed.has(targetId)) {
                    routes.push(routeFor(track, rules.filter((rule) => rule.target_id === targetId), content.id));
                }
            }
            return { content, isBranchPoint: rules.length > 0, rules, routes };
        });
    }

    const spine = nodesOn(null);

    const unrouted = [];
    for (const track of tracks.filter((candidate) => !placed.has(candidate.id)).sort((a, b) => a.id - b.id)) {
        if (!placed.has(track.id)) {
            unrouted.push(routeFor(track, [], null));
        }
    }

    const orphans = [...contentsByTrack.keys()]
        .filter((trackId) => trackId !== null && !trackById.has(trackId))
        .flatMap((trackId) => nodesOn(trackId));

    return { spine, unrouted, orphans };
}

/**
 * The rows of the content table, in display order.
 *
 * - `{ kind: 'content', content, depth, isBranchPoint }`
 * - `{ kind: 'branch', track, rules, alsoFrom, depth }` - opens a track
 * - `{ kind: 'rejoin', track, mergeContent, depth }` - closes it
 * - `{ kind: 'unrouted', depth }` - heads the tracks no rule reaches
 */
export function buildContentTree(contents, tracks = [], transitions = []) {
    const { spine, unrouted, orphans } = buildRouteTree(contents, tracks, transitions);
    const rows = [];

    const pushRoute = (route, depth) => {
        rows.push({ kind: 'branch', key: `branch-${route.track.id}`, track: route.track, rules: route.rules, alsoFrom: route.alsoFrom, depth });
        pushNodes(route.nodes, depth);
        rows.push({ kind: 'rejoin', key: `rejoin-${route.track.id}`, track: route.track, mergeContent: route.mergeContent, depth });
    };

    function pushNodes(nodes, depth) {
        for (const node of nodes) {
            rows.push({ kind: 'content', key: `content-${node.content.id}`, content: node.content, depth, isBranchPoint: node.isBranchPoint });
            for (const route of node.routes) {
                pushRoute(route, depth + 1);
            }
        }
    }

    pushNodes(spine, 0);
    if (unrouted.length > 0) {
        rows.push({ kind: 'unrouted', key: 'unrouted', depth: 0 });
        for (const route of unrouted) {
            pushRoute(route, 1);
        }
    }
    pushNodes(orphans, 0);
    return rows;
}

// A select holds '' for the main path; the API holds null.
export const toTrackValue = (trackId) => (trackId == null ? '' : trackId);
export const fromTrackValue = (value) => (value === '' ? null : Number(value));
