/**
 * A branching course as a graph, for the course map.
 *
 * Nodes are the course's contents plus one end node. Edges are every way a learner can move:
 * to the next content on the same track, onto a track a routing rule selects, back to where a
 * finished track rejoins, or on to the end of the course. Each edge carries a `kind` so the map
 * can style and label it; positions are left to the layout.
 *
 * Edge kinds:
 * - `next` - the following content on the same track
 * - `route` - onto a track, carrying the `rules` that select it
 * - `otherwise` - a branch point's plain next step, taken when no rule matches
 * - `unsubmitted` - the same step behind an otherwise rule, taken only when there is no result
 *   to route by, since rules are ignored then
 * - `rejoin` - from the last content on a track to where it continues
 * - `ends` - from the last content on a track that ends the course
 */

export const END_NODE_ID = 'end';
export const contentNodeId = (contentId) => `content-${contentId}`;

const trackOf = (content) => content.track_id ?? null;

export function buildFlowGraph(contents, tracks = [], transitions = []) {
    const lanes = new Map();
    for (const content of contents) {
        const trackId = trackOf(content);
        if (!lanes.has(trackId)) {
            lanes.set(trackId, []);
        }
        lanes.get(trackId).push(content);
    }
    const contentIds = new Set(contents.map((content) => content.id));
    const trackById = new Map(tracks.map((track) => [track.id, track]));

    const rulesBySource = new Map();
    const routedTracks = new Set();
    for (const rule of [...transitions].sort((a, b) => a.order - b.order)) {
        if (!rulesBySource.has(rule.source_id)) {
            rulesBySource.set(rule.source_id, []);
        }
        rulesBySource.get(rule.source_id).push(rule);
        routedTracks.add(rule.target_id);
    }

    // Where a learner goes once a track runs out: its merge point, or that of a track it branches off.
    const continuationOf = (trackId) => {
        const seen = new Set();
        let track = trackById.get(trackId);
        while (track && !seen.has(track.id)) {
            seen.add(track.id);
            if (track.merge_into_id != null && contentIds.has(track.merge_into_id)) {
                return contentNodeId(track.merge_into_id);
            }
            track = track.parent_track_id != null ? trackById.get(track.parent_track_id) : undefined;
        }
        return END_NODE_ID;
    };

    const successorOf = (content) => {
        const lane = lanes.get(trackOf(content));
        const index = lane.indexOf(content);
        if (index < lane.length - 1) {
            return { target: contentNodeId(lane[index + 1].id), leavesTrack: false };
        }
        if (trackOf(content) === null) {
            return { target: END_NODE_ID, leavesTrack: false };
        }
        return { target: continuationOf(trackOf(content)), leavesTrack: true };
    };

    const entryOf = (trackId) => {
        const lane = lanes.get(trackId);
        return lane && lane.length > 0 ? contentNodeId(lane[0].id) : continuationOf(trackId);
    };

    const trackFor = (content) => (trackOf(content) === null ? null : trackById.get(trackOf(content)) ?? null);

    const nodes = contents.map((content) => ({
        id: contentNodeId(content.id),
        type: 'content',
        data: {
            content,
            track: trackFor(content),
            isBranchPoint: rulesBySource.has(content.id),
            unreached: trackOf(content) !== null && !routedTracks.has(trackOf(content)),
        },
    }));
    nodes.push({ id: END_NODE_ID, type: 'end', data: {} });

    const edges = [];
    for (const content of contents) {
        const source = contentNodeId(content.id);
        const track = trackFor(content);
        const { target: next, leavesTrack } = successorOf(content);
        const rules = rulesBySource.get(content.id) || [];

        if (rules.length === 0) {
            const kind = !leavesTrack ? 'next' : next === END_NODE_ID ? 'ends' : 'rejoin';
            edges.push({ id: `${source}-next`, source, target: next, data: { kind, track } });
            continue;
        }

        const targets = [];
        for (const rule of rules) {
            if (trackById.has(rule.target_id) && !targets.includes(rule.target_id)) {
                targets.push(rule.target_id);
            }
        }
        for (const trackId of targets) {
            edges.push({
                id: `${source}-route-${trackId}`,
                source,
                target: entryOf(trackId),
                data: { kind: 'route', track: trackById.get(trackId), rules: rules.filter((rule) => rule.target_id === trackId) },
            });
        }

        const catchesEverything = rules.some((rule) => rule.condition === 'default');
        edges.push({
            id: `${source}-fallthrough`,
            source,
            target: next,
            data: { kind: catchesEverything ? 'unsubmitted' : 'otherwise', track },
        });
    }

    return { nodes, edges };
}
