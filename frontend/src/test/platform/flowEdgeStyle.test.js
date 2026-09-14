import { describe, it, expect } from 'vitest';
import { createTheme } from '@mui/material/styles';
import { Position } from '@xyflow/react';
import { REJOIN_TURN, rejoinPath, styleEdge } from '../../../platform/course/components/flowEdgeStyle.js';

const theme = createTheme();
const remedial = { id: 7, name: 'Remedial' };
const context = {
    theme,
    localeMessages: { branch_condition_failed: 'If failed' },
    trackColors: new Map([[7, '#7e57c2']]),
};
const route = (inactive) => ({
    id: 'content-2-route-7',
    source: 'content-2',
    target: 'content-10',
    data: { kind: 'route', track: remedial, rules: [{ condition: 'failed', threshold: null }], inactive },
});

describe('styleEdge', () => {
    it('draws a route solid in its track colour, labelled with its rule', () => {
        const edge = styleEdge(route(false), context);

        expect(edge.style.stroke).toBe('#7e57c2');
        expect(edge.style.strokeDasharray).toBeUndefined();
        expect(edge.label).toBe('If failed');
    });

    it('dots and fades a route out of unpublished content, keeping its label', () => {
        const edge = styleEdge(route(true), context);

        expect(edge.style.strokeDasharray).toBe('2 4');
        expect(edge.style.opacity).toBe(0.7);
        expect(edge.style.strokeWidth).toBe(1.5);
        expect(edge.label).toBe('If failed');
    });

    it('draws the step past unpublished content solid, even where it leaves the track', () => {
        const rejoin = (taken) => ({ id: 'content-11-next', source: 'content-11', target: 'content-3', data: { kind: 'rejoin', track: remedial, taken } });

        expect(styleEdge(rejoin(undefined), context).style.strokeDasharray).toBe('6 4');
        expect(styleEdge(rejoin(true), context).style.strokeDasharray).toBeUndefined();
    });

    it('draws the arrows leaving a track with the rejoin line, and the rest as plain steps', () => {
        const edge = (kind) => ({ id: kind, source: 'a', target: 'b', data: { kind, track: remedial } });

        expect(styleEdge(edge('rejoin'), context).type).toBe('rejoin');
        expect(styleEdge(edge('ends'), context).type).toBe('rejoin');
        expect(styleEdge(edge('next'), context).type).toBe('smoothstep');
        expect(styleEdge(route(false), context).type).toBe('smoothstep');
    });
});

describe('rejoinPath', () => {
    it('turns across just above the content it continues at, however far below that is', () => {
        const horizontalRunY = (sourceY, targetY) => {
            const path = rejoinPath({ sourceX: 600, sourceY, sourcePosition: Position.Bottom, targetX: 120, targetY, targetPosition: Position.Top });
            const ys = [...path.matchAll(/[ML]\s*([-\d.]+)[ ,]([-\d.]+)/g)].map((match) => Number(match[2]));
            return ys;
        };

        // One row down and four rows down: the line reaches the same height before it turns.
        expect(horizontalRunY(100, 244)).toContain(244 - REJOIN_TURN);
        expect(horizontalRunY(100, 676)).toContain(676 - REJOIN_TURN);
    });
});
