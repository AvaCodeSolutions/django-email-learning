import { describe, it, expect, vi } from 'vitest';
import { screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import QuizBranching from '../../../platform/course/components/QuizBranching';

vi.mock('../../render.jsx');

const localeMessages = {
    branching_rules_help: 'Rules are checked from top to bottom.',
    branching_no_tracks: 'This course has no tracks yet.',
    add_rule: 'Add rule',
    save_rules: 'Save rules',
    rules_saved: 'Routing rules saved.',
    rules_save_failed: 'Could not save the routing rules.',
    rule_condition: 'When',
    rule_threshold: 'Score',
    rule_target: 'Send to',
    condition_passed: 'Passed',
    condition_failed: 'Failed',
    condition_score_gte: 'Score at least',
    condition_score_lt: 'Score below',
    condition_default: 'Otherwise',
    move_rule_up: 'Move rule up',
    move_rule_down: 'Move rule down',
    remove_rule: 'Remove rule',
    rule_threshold_required: 'A score rule needs a score between 0 and 100.',
};

const tracks = [
    { id: 7, name: 'Remedial', parent_track_id: null, merge_into_id: 3 },
    { id: 8, name: 'Advanced', parent_track_id: null, merge_into_id: 3 },
];

const json = (body, status = 200) => Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) });

function mockApi({ transitions = [], trackList = tracks, putResponse } = {}) {
    global.fetch.mockImplementation((url, options = {}) => {
        if (options.method === 'PUT') {
            if (putResponse) {
                return putResponse;
            }
            const sent = JSON.parse(options.body).transitions;
            return json({ transitions: sent.map((rule, index) => ({ id: index + 1, source_id: 3, order: index + 1, ...rule })) });
        }
        if (url.endsWith('/tracks/')) {
            return json({ tracks: trackList });
        }
        return json({ transitions });
    });
}

function setup({ role = 'editor', onChange = vi.fn() } = {}) {
    window.localStorage.setItem('activeOrganizationId', '1');
    renderWithProviders(
        <QuizBranching courseId={5} contentId={3} onChange={onChange} />,
        { appContext: { apiBaseUrl: '/api', localeMessages, userRole: role } },
    );
    return { onChange };
}

const putCall = () => global.fetch.mock.calls.find(([, options]) => options?.method === 'PUT');

describe('QuizBranching', () => {
    it('shows the saved rules in their order', async () => {
        mockApi({ transitions: [
            { id: 1, source_id: 3, order: 1, condition: 'failed', threshold: null, target_id: 7 },
            { id: 2, source_id: 3, order: 2, condition: 'default', threshold: null, target_id: 8 },
        ] });
        setup();

        const rules = await screen.findAllByTestId('routing-rule');

        expect(rules).toHaveLength(2);
        expect(within(rules[0]).getByRole('combobox', { name: 'When' })).toHaveTextContent('Failed');
        expect(within(rules[0]).getByRole('combobox', { name: 'Send to' })).toHaveTextContent('Remedial');
        expect(within(rules[1]).getByRole('combobox', { name: 'When' })).toHaveTextContent('Otherwise');
    });

    it('explains there is nothing to route onto before a track exists', async () => {
        mockApi({ trackList: [] });
        setup();

        expect(await screen.findByText('This course has no tracks yet.')).toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Add rule' })).not.toBeInTheDocument();
    });

    it('saves the whole rule set in the order shown', async () => {
        mockApi({ transitions: [{ id: 1, source_id: 3, order: 1, condition: 'passed', threshold: null, target_id: 8 }] });
        const user = userEvent.setup();
        const { onChange } = setup();
        await screen.findAllByTestId('routing-rule');

        await user.click(screen.getByRole('button', { name: 'Add rule' }));
        await user.click(screen.getByRole('button', { name: 'Save rules' }));

        expect(await screen.findByText('Routing rules saved.')).toBeInTheDocument();
        const [url, options] = putCall();
        expect(url).toBe('/api/organizations/1/courses/5/contents/3/transitions/');
        expect(JSON.parse(options.body).transitions).toEqual([
            { condition: 'passed', threshold: null, option_id: null, target_id: 8 },
            { condition: 'failed', threshold: null, option_id: null, target_id: 7 },
        ]);
        expect(onChange).toHaveBeenCalledWith(2);
    });

    it('adds a new rule in front of an otherwise rule, which would shadow it', async () => {
        mockApi({ transitions: [{ id: 1, source_id: 3, order: 1, condition: 'default', threshold: null, target_id: 8 }] });
        const user = userEvent.setup();
        setup();
        await screen.findAllByTestId('routing-rule');

        await user.click(screen.getByRole('button', { name: 'Add rule' }));

        const rules = screen.getAllByTestId('routing-rule');
        expect(within(rules[0]).getByRole('combobox', { name: 'When' })).toHaveTextContent('Failed');
        expect(within(rules[1]).getByRole('combobox', { name: 'When' })).toHaveTextContent('Otherwise');
    });

    it('reorders rules before saving', async () => {
        mockApi({ transitions: [
            { id: 1, source_id: 3, order: 1, condition: 'failed', threshold: null, target_id: 7 },
            { id: 2, source_id: 3, order: 2, condition: 'passed', threshold: null, target_id: 8 },
        ] });
        const user = userEvent.setup();
        setup();
        const rules = await screen.findAllByTestId('routing-rule');

        await user.click(within(rules[1]).getByRole('button', { name: 'Move rule up' }));
        await user.click(screen.getByRole('button', { name: 'Save rules' }));

        await screen.findByText('Routing rules saved.');
        expect(JSON.parse(putCall()[1].body).transitions.map((rule) => rule.condition)).toEqual(['passed', 'failed']);
    });

    it('asks for a score before saving a score rule without one', async () => {
        mockApi({ transitions: [{ id: 1, source_id: 3, order: 1, condition: 'score_lt', threshold: 50, target_id: 7 }] });
        const user = userEvent.setup();
        setup();
        const rules = await screen.findAllByTestId('routing-rule');

        await user.clear(within(rules[0]).getByLabelText('Score'));
        await user.click(screen.getByRole('button', { name: 'Save rules' }));

        expect(await screen.findByText('A score rule needs a score between 0 and 100.')).toBeInTheDocument();
        expect(putCall()).toBeUndefined();
    });

    it('shows why the server refused the rules', async () => {
        mockApi({
            transitions: [{ id: 1, source_id: 3, order: 1, condition: 'failed', threshold: null, target_id: 7 }],
            putResponse: json({ error: ["'Remedial' rejoins the course at or before this content."] }, 400),
        });
        const user = userEvent.setup();
        setup();
        await screen.findAllByTestId('routing-rule');

        await user.click(screen.getByRole('button', { name: 'Save rules' }));

        expect(await screen.findByText(/rejoins the course at or before/)).toBeInTheDocument();
    });

    it('is read-only for a viewer', async () => {
        mockApi({ transitions: [{ id: 1, source_id: 3, order: 1, condition: 'failed', threshold: null, target_id: 7 }] });
        setup({ role: 'viewer' });
        const rules = await screen.findAllByTestId('routing-rule');

        await waitFor(() => expect(within(rules[0]).getByRole('combobox', { name: 'When' })).toHaveAttribute('aria-disabled', 'true'));
        expect(screen.queryByRole('button', { name: 'Add rule' })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: 'Save rules' })).not.toBeInTheDocument();
    });
});

describe('QuizBranching on a decision point', () => {
    const options = [{ id: 11, text: 'Basics' }, { id: 12, text: 'Deeper dive' }];
    const renderDecisionRules = () => {
        window.localStorage.setItem('activeOrganizationId', '1');
        renderWithProviders(
            <QuizBranching courseId={5} contentId={3} options={options} />,
            { appContext: { apiBaseUrl: '/api', userRole: 'editor', localeMessages: { ...localeMessages, condition_option_selected: 'Answered', rule_option: 'Answer' } } },
        );
    };

    it('offers only answer rules and an otherwise rule', async () => {
        mockApi();
        const user = userEvent.setup();
        renderDecisionRules();

        await user.click(await screen.findByRole('button', { name: 'Add rule' }));
        await user.click(within(screen.getByTestId('routing-rule')).getByRole('combobox', { name: 'When' }));

        expect(screen.getAllByRole('option').map((option) => option.textContent)).toEqual(['Answered', 'Otherwise']);
    });

    it('saves the answer each rule matches', async () => {
        mockApi();
        const user = userEvent.setup();
        renderDecisionRules();

        await user.click(await screen.findByRole('button', { name: 'Add rule' }));
        await user.click(within(screen.getByTestId('routing-rule')).getByRole('combobox', { name: 'Answer' }));
        await user.click(screen.getByRole('option', { name: 'Deeper dive' }));
        await user.click(screen.getByRole('button', { name: 'Save rules' }));

        await waitFor(() => expect(putCall()).toBeDefined());
        expect(JSON.parse(putCall()[1].body).transitions).toEqual([
            { condition: 'option_selected', threshold: null, option_id: 12, target_id: 7 },
        ]);
    });
});
