import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import DecisionForm from '../../../platform/course/components/DecisionForm';

vi.mock('../../render.jsx');

const localeMessages = {
    title: 'Title',
    new_decision: 'New Decision',
    decision_prompt: 'Question',
    decision_options: 'Answers',
    decision_option_label: 'Answer %(number)s',
    decision_add_option: 'Add answer',
    decision_remove_option: 'Remove answer',
    decision_move_option_up: 'Move answer up',
    decision_move_option_down: 'Move answer down',
    decision_options_required: 'A decision needs at least two answers, and none of them can be empty.',
    save_decision: 'Save Decision',
    decision_tab_question: 'Question',
    quiz_tab_branching: 'Branching',
    cancel: 'Cancel',
    days: 'Days',
    hours: 'Hours',
    period: 'Period',
    rule_condition: 'When',
    rule_option: 'Answer',
    rule_target: 'Send to',
    add_rule: 'Add rule',
    save_rules: 'Save rules',
    condition_option_selected: 'Answered',
    condition_default: 'Otherwise',
};

const json = (body, status = 200) => Promise.resolve({ ok: status < 400, status, json: () => Promise.resolve(body) });

const savedDecision = {
    id: 9,
    decision: {
        id: 4,
        title: 'Pick',
        prompt: 'Where next?',
        options: [{ id: 11, text: 'Basics', order: 1 }, { id: 12, text: 'Advanced', order: 2 }],
    },
};

const renderForm = (props = {}) => {
    window.localStorage.setItem('activeOrganizationId', '1');
    return renderWithProviders(
        <DecisionForm courseId={5} {...props} />,
        { appContext: { apiBaseUrl: '/api', localeMessages, userRole: 'editor' } },
    );
};

const existing = {
    contentId: 9,
    initialTitle: 'Pick',
    initialPrompt: 'Where next?',
    initialOptions: [{ id: 11, text: 'Basics' }, { id: 12, text: 'Advanced' }, { id: 13, text: 'Unsure' }],
    initialDeadlineDays: 0,
    initialWaitingPeriod: { period: 1, type: 'days' },
};

const postCall = () => global.fetch.mock.calls.find(([, options]) => options?.method === 'POST');

describe('DecisionForm', () => {
    beforeEach(() => {
        global.fetch.mockClear();
        global.fetch.mockImplementation(() => json(savedDecision));
    });

    it('creates a decision with its answers in order', async () => {
        const successCallback = vi.fn();
        const user = userEvent.setup();
        renderForm({ successCallback });

        await user.type(screen.getByLabelText(/Title/), 'Pick');
        await user.type(screen.getByLabelText(/^Question/), 'Where next?');
        await user.type(screen.getByLabelText(/Answer 1/), 'Basics');
        await user.type(screen.getByLabelText(/Answer 2/), 'Advanced');
        await user.click(screen.getByRole('button', { name: 'Save Decision' }));

        await waitFor(() => expect(successCallback).toHaveBeenCalled());
        const [url, options] = postCall();
        expect(url).toBe('/api/organizations/1/courses/5/contents/');
        expect(JSON.parse(options.body).content).toEqual({
            type: 'decision',
            title: 'Pick',
            prompt: 'Where next?',
            deadline_days: 0,
            reminder_interval_days: 0,
            options: [{ text: 'Basics' }, { text: 'Advanced' }],
        });
    });

    it('refuses to save a decision with an empty answer', async () => {
        const user = userEvent.setup();
        renderForm();

        await user.type(screen.getByLabelText(/Title/), 'Pick');
        await user.type(screen.getByLabelText(/^Question/), 'Where next?');
        await user.type(screen.getByLabelText(/Answer 1/), 'Basics');
        await user.click(screen.getByRole('button', { name: 'Save Decision' }));

        expect(screen.getByText(localeMessages.decision_options_required)).toBeInTheDocument();
        expect(postCall()).toBeUndefined();
    });

    it('keeps at least two answers', () => {
        renderForm();

        for (const button of screen.getAllByRole('button', { name: 'Remove answer' })) {
            expect(button).toBeDisabled();
        }
    });

    it('saves edited answers by id, new ones without, and leaves removed ones out', async () => {
        const user = userEvent.setup();
        renderForm(existing);

        await user.click(within(screen.getAllByTestId('decision-option')[2]).getByRole('button', { name: 'Remove answer' }));
        await user.click(screen.getByRole('button', { name: 'Add answer' }));
        await user.type(screen.getByLabelText(/Answer 3/), 'Both');
        await user.click(within(screen.getAllByTestId('decision-option')[1]).getByRole('button', { name: 'Move answer up' }));
        await user.click(screen.getByRole('button', { name: 'Save Decision' }));

        await waitFor(() => expect(postCall()).toBeDefined());
        const [url, options] = postCall();
        expect(url).toBe('/api/organizations/1/courses/5/contents/9/');
        expect(JSON.parse(options.body).decision.options).toEqual([
            { id: 12, text: 'Advanced' },
            { id: 11, text: 'Basics' },
            { text: 'Both' },
        ]);
    });

    it('routes on the saved answers in the Branching tab', async () => {
        global.fetch.mockImplementation((url) => (url.endsWith('/tracks/')
            ? json({ tracks: [{ id: 7, name: 'Basics track', parent_track_id: null, merge_into_id: null }] })
            : json({ transitions: [] })));
        const user = userEvent.setup();
        renderForm(existing);

        await user.click(screen.getByRole('tab', { name: 'Branching' }));
        await user.click(await screen.findByRole('button', { name: 'Add rule' }));

        const rule = screen.getByTestId('routing-rule');
        expect(within(rule).getByRole('combobox', { name: 'When' })).toHaveTextContent('Answered');
        expect(within(rule).getByRole('combobox', { name: 'Answer' })).toHaveTextContent('Basics');
    });
});
