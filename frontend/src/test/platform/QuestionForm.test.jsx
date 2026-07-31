import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import QuestionForm from '../../../platform/course/components/QuestionForm';

vi.mock('../../render.jsx');

const localeMessages = {
  add_option: 'Add Option',
  delete: 'Delete',
  options: 'Options',
  correct_answer: 'Correct Answer',
  actions: 'Actions',
  add: 'Add',
  cancel: 'Cancel',
};

const makeQuestion = (overrides = {}) => ({
  _clientId: 'q1',
  id: null,
  text: 'What is 2 + 2?',
  options: [],
  ...overrides,
});

describe('QuestionForm', () => {
  it('renders the question text', () => {
    renderWithProviders(
      <QuestionForm question={makeQuestion()} index={0} eventHandler={vi.fn()} />,
      { appContext: { localeMessages, userRole: 'editor' } }
    );
    expect(screen.getByText('What is 2 + 2?')).toBeInTheDocument();
  });

  it('renders add option and delete buttons for non-viewer role', () => {
    renderWithProviders(
      <QuestionForm question={makeQuestion()} index={0} eventHandler={vi.fn()} />,
      { appContext: { localeMessages, userRole: 'editor' } }
    );
    expect(screen.getByRole('button', { name: 'Add Option' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
  });

  it('does not render action buttons for viewer role', () => {
    renderWithProviders(
      <QuestionForm question={makeQuestion()} index={0} eventHandler={vi.fn()} />,
      { appContext: { localeMessages, userRole: 'viewer' } }
    );
    expect(screen.queryByRole('button', { name: 'Add Option' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument();
  });

  it('dispatches delete_question event when delete is clicked', async () => {
    const user = userEvent.setup();
    const eventHandler = vi.fn();
    renderWithProviders(
      <QuestionForm question={makeQuestion()} index={0} eventHandler={eventHandler} />,
      { appContext: { localeMessages, userRole: 'editor' } }
    );
    await user.click(screen.getByRole('button', { name: 'Delete' }));
    expect(eventHandler).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'delete_question' })
    );
  });

  it('renders existing options in a table', () => {
    const question = makeQuestion({
      options: [
        { optionText: '4', isCorrect: true, editMode: false },
        { optionText: '5', isCorrect: false, editMode: false },
      ],
    });
    renderWithProviders(
      <QuestionForm question={question} index={0} eventHandler={vi.fn()} />,
      { appContext: { localeMessages, userRole: 'editor' } }
    );
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });
});
