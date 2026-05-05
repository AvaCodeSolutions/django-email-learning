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
