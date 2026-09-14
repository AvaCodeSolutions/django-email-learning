import { describe, it, expect } from 'vitest';
import { createTheme } from '@mui/material/styles';
import { styleEdge } from '../../../platform/course/components/flowEdgeStyle.js';

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
        expect(edge.label).toBe('If failed');
    });
});
