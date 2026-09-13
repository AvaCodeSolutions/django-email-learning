import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import ContentTable from '../../../platform/course/components/ContentTable';

vi.mock('../../render.jsx');

const localeMessages = {
  title: 'Title',
  waiting_time: 'Waiting Time',
  type: 'Type',
  published: 'Published',
  actions: 'Actions',
  delete: 'Delete',
  lesson: 'Lesson',
  quiz: 'Quiz',
  assignment: 'Assignment',
  practice_quiz: 'Practice',
  two_attempts: '2 Attempts',
  unlimited_attempts: 'Unlimited',
  quiz_2_attempts_sub_note: 'Two attempts allowed.',
  quiz_unlimited_attempts_sub_note: 'Unlimited attempts allowed.',
  send_lesson_to_yourself: 'Send to yourself',
  send_lesson: 'Send lesson',
  lesson_sent_to_your_email: 'Lesson sent to your email.',
};

const sampleContents = [
  { id: '1', title: 'Welcome Lesson', type: 'lesson', waiting_period: null, is_published: true },
  { id: '2', title: 'First Quiz', type: 'quiz', waiting_period: null, is_published: false, is_blocking: true, limited_attempts: null },
];

describe('ContentTable', () => {
  beforeEach(() => {
    window.localStorage.setItem('activeOrganizationId', '1');
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ course_contents: [] }),
    });
  });

  it('renders table headers', async () => {
    renderWithProviders(
      <ContentTable courseId="5" eventHandler={vi.fn()} />,
      { appContext: { localeMessages, userRole: 'editor' } }
    );
    await waitFor(() => expect(screen.getByText('Title')).toBeInTheDocument());
    expect(screen.getByText('Type')).toBeInTheDocument();
    expect(screen.getByText('Published')).toBeInTheDocument();
  });

  it('renders content rows after fetch', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ course_contents: sampleContents }),
    });
    renderWithProviders(
      <ContentTable courseId="5" eventHandler={vi.fn()} />,
      { appContext: { localeMessages, userRole: 'editor' } }
    );
    await waitFor(() => expect(screen.getByText('Welcome Lesson')).toBeInTheDocument());
    expect(screen.getByText('First Quiz')).toBeInTheDocument();
  });

  it('dispatches delete_content event when delete is clicked', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ course_contents: sampleContents }),
    });
    const eventHandler = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(
      <ContentTable courseId="5" eventHandler={eventHandler} />,
      { appContext: { localeMessages, userRole: 'editor' } }
    );
    await waitFor(() => expect(screen.getByText('Welcome Lesson')).toBeInTheDocument());
    await user.click(screen.getAllByRole('button', { name: 'Delete' })[0]);
    expect(eventHandler).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'delete_content' })
    );
  });

  it('dispatches content_clicked event when content title is clicked', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ course_contents: sampleContents }),
    });
    const eventHandler = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(
      <ContentTable courseId="5" eventHandler={eventHandler} />,
      { appContext: { localeMessages, userRole: 'editor' } }
    );
    await waitFor(() => expect(screen.getByText('Welcome Lesson')).toBeInTheDocument());
    await user.click(screen.getByText('Welcome Lesson'));
    expect(eventHandler).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'content_clicked', content_id: '1' })
    );
  });
});

describe('ContentTable branching', () => {
  const branchingMessages = {
    ...localeMessages,
    rejoins_at: 'Rejoins at TITLE',
    ends_the_course: 'Ends the course',
    branch_condition_failed: 'If failed',
    move_to_track: 'Move to',
    main_path: 'Main path',
    edit_track: 'Edit Track',
    delete_track: 'Delete Track',
    quiz_tab_branching: 'Branching',
  };

  const structure = {
    course_contents: [
      { id: 1, title: 'Intro', type: 'lesson', track_id: null, waiting_period: null, is_published: true },
      { id: 10, title: 'Remedial lesson', type: 'lesson', track_id: 7, waiting_period: null, is_published: true },
      { id: 2, title: 'Checkpoint', type: 'quiz', track_id: null, waiting_period: null, is_published: true, is_blocking: true, limited_attempts: true },
      { id: 3, title: 'Wrap up', type: 'lesson', track_id: null, waiting_period: null, is_published: true },
    ],
    tracks: [{ id: 7, name: 'Remedial', parent_track_id: null, merge_into_id: 3 }],
    transitions: [{ id: 1, source_id: 2, order: 1, condition: 'failed', threshold: null, target_id: 7 }],
  };

  const renderTable = (role = 'editor', eventHandler = vi.fn()) => {
    global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(structure) });
    renderWithProviders(
      <ContentTable courseId="5" eventHandler={eventHandler} />,
      { appContext: { localeMessages: branchingMessages, userRole: role } }
    );
    return eventHandler;
  };

  it('renders a track under the quiz that routes onto it', async () => {
    renderTable();
    await screen.findByText('Remedial lesson');

    const rowTexts = screen.getAllByRole('row').map((row) => row.textContent);
    const position = (text) => rowTexts.findIndex((rowText) => rowText.includes(text));
    expect(position('Checkpoint')).toBeLessThan(position('If failed'));
    expect(position('If failed')).toBeLessThan(position('Remedial lesson'));
    expect(position('Remedial lesson')).toBeLessThan(position('Rejoins at Wrap up'));
  });

  it('marks a branch point instead of showing its attempt limit', async () => {
    renderTable();
    await screen.findByText('Remedial lesson');

    expect(screen.queryByText('2 Attempts')).not.toBeInTheDocument();
    expect(screen.getByText('Branching')).toBeInTheDocument();
  });

  it('moves content onto a track from the row menu', async () => {
    const user = userEvent.setup();
    const eventHandler = renderTable();
    await screen.findByText('Remedial lesson');

    await user.click(screen.getAllByRole('button', { name: 'Move to: Intro' })[0]);
    await user.click(screen.getByRole('menuitem', { name: 'Remedial' }));

    expect(eventHandler).toHaveBeenCalledWith({ type: 'content_moved', content_id: 1, track_id: 7 });
  });

  it('opens a track for editing from its header', async () => {
    const user = userEvent.setup();
    const eventHandler = renderTable();
    await screen.findByText('Remedial lesson');

    await user.click(screen.getByRole('button', { name: 'Edit Track: Remedial' }));

    expect(eventHandler).toHaveBeenCalledWith(expect.objectContaining({ type: 'edit_track', track: expect.objectContaining({ id: 7 }) }));
  });

  it('hides the authoring controls from a viewer', async () => {
    renderTable('viewer');
    await screen.findByText('Remedial lesson');

    expect(screen.queryByRole('button', { name: 'Edit Track: Remedial' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Move to: Intro' })).not.toBeInTheDocument();
  });
});

describe('ContentTable publishing', () => {
  it('tells the page once a publish toggle is saved', async () => {
    global.fetch.mockImplementation((url, options) => {
      if (options?.method === 'POST') {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ course_contents: sampleContents }) });
    });
    const eventHandler = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(
      <ContentTable courseId="5" eventHandler={eventHandler} />,
      { appContext: { localeMessages, userRole: 'editor' } }
    );
    await screen.findByText('First Quiz');

    await user.click(screen.getAllByLabelText('Published: First Quiz')[0]);

    await waitFor(() => expect(eventHandler).toHaveBeenCalledWith({ type: 'content_published', content_id: '2', is_published: true }));
  });
});
