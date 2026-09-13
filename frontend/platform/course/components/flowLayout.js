import dagre from '@dagrejs/dagre';

export const NODE_WIDTH = 240;
export const NODE_HEIGHT = 72;

/**
 * Top-to-bottom positions for the course map.
 *
 * dagre ranks the graph so every edge points downward: the main path reads top to bottom,
 * the tracks a branch point routes onto fan out beside it, and a track's rejoin lands on its
 * merge point further down.
 */
export function layoutFlow(nodes, edges) {
    const graph = new dagre.graphlib.Graph();
    graph.setGraph({ rankdir: 'TB', nodesep: 48, ranksep: 72 });
    graph.setDefaultEdgeLabel(() => ({}));
    for (const node of nodes) {
        graph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    }
    for (const edge of edges) {
        graph.setEdge(edge.source, edge.target);
    }
    dagre.layout(graph);
    return nodes.map((node) => {
        const { x, y } = graph.node(node.id);
        return { ...node, position: { x: x - NODE_WIDTH / 2, y: y - NODE_HEIGHT / 2 } };
    });
}
