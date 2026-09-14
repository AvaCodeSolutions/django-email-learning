import { describe, it, expect, vi, beforeAll } from 'vitest';
import { fireEvent, screen } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import CourseMap from '../../../platform/course/components/CourseMap.jsx';

vi.mock('../../render.jsx');

// React Flow measures nodes and observes resizes, neither of which jsdom implements.
beforeAll(() => {
    global.ResizeObserver = class {
        constructor(callback) {
            this.callback = callback;
        }
        observe(target) {
            // The pan/zoom setup reads the viewport's size straight off the entry.
            const width = target.offsetWidth || 960;
            const height = target.offsetHeight || 640;
            this.callback([{
                target,
                contentRect: { width, height, top: 0, left: 0, right: width, bottom: height, x: 0, y: 0 },
                borderBoxSize: [{ inlineSize: width, blockSize: height }],
                contentBoxSize: [{ inlineSize: width, blockSize: height }],
            }]);
        }
        unobserve() {}
        disconnect() {}
    };
    global.DOMMatrixReadOnly = class {
        constructor(transform) {
            const scale = transform?.match(/scale\(([\d.]+)\)/)?.[1];
            this.m22 = scale !== undefined ? Number(scale) : 1;
        }
    };
    Object.defineProperties(global.HTMLElement.prototype, {
        offsetHeight: { configurable: true, get() { return parseFloat(this.style.height) || 72; } },
        offsetWidth: { configurable: true, get() { return parseFloat(this.style.width) || 240; } },
    });
    global.SVGElement.prototype.getBBox = () => ({ x: 0, y: 0, width: 40, height: 16 });
});

const localeMessages = {
    main_path: 'Main path',
    not_published: 'Not published',
    map_unreached: 'No rule routes here',
    map_course_complete: 'Course complete',
    course_view_flow: 'Flow',
    edit_track: 'Edit Track',
};

const contents = [
    { id: 1, title: 'Intro', type: 'lesson', track_id: null, is_published: true },
    { id: 10, title: 'Remedial lesson', type: 'lesson', track_id: 7, is_published: true },
    { id: 2, title: 'Checkpoint', type: 'quiz', track_id: null, is_published: true },
    { id: 3, title: 'Wrap up', type: 'lesson', track_id: null, is_published: false },
];
const remedial = { id: 7, name: 'Remedial', parent_track_id: null, merge_into_id: 3 };
const failedRule = { id: 1, source_id: 2, order: 1, condition: 'failed', threshold: null, target_id: 7 };

function renderMap(props = {}) {
    const onContentClick = vi.fn();
    renderWithProviders(
        <CourseMap contents={contents} tracks={[remedial]} transitions={[failedRule]} onContentClick={onContentClick} {...props} />,
        { appContext: { localeMessages } },
    );
    return onContentClick;
}

describe('CourseMap', () => {
    it('draws every content, naming the track it is on', () => {
        renderMap();

        expect(screen.getByText('Intro')).toBeInTheDocument();
        expect(screen.getByText('Remedial lesson')).toBeInTheDocument();
        expect(screen.getByText('Remedial')).toBeInTheDocument();
        expect(screen.getByText('Course complete')).toBeInTheDocument();
    });

    it('marks unpublished content and tracks no rule reaches', () => {
        renderMap({ transitions: [] });

        expect(screen.getByText('Not published')).toBeInTheDocument();
        expect(screen.getByText('No rule routes here')).toBeInTheDocument();
    });

    it('opens content from its node, by pointer or keyboard', () => {
        const onContentClick = renderMap();

        fireEvent.click(screen.getByText('Remedial lesson'));
        const introNode = screen.getByText('Intro').closest('[role="button"]');
        expect(introNode).not.toBeNull();
        expect(introNode).toHaveAttribute('aria-label', 'Intro');
        fireEvent.keyDown(introNode, { key: 'Enter' });

        expect(onContentClick).toHaveBeenCalledWith(10);
        expect(onContentClick).toHaveBeenCalledWith(1);
    });

    it('opens a track for editing from its name', () => {
        const onTrackClick = vi.fn();
        renderMap({ onTrackClick });

        const trackName = screen.getByText('Remedial').closest('button');
        expect(trackName).not.toBeNull();
        expect(trackName).toHaveAttribute('aria-label', 'Edit Track: Remedial');
        fireEvent.click(trackName);

        expect(onTrackClick).toHaveBeenCalledWith(expect.objectContaining({ id: 7, name: 'Remedial' }));
    });

    it('shows the track name as plain text when tracks cannot be edited', () => {
        renderMap();

        expect(screen.getByText('Remedial').closest('button')).toBeNull();
    });
});
