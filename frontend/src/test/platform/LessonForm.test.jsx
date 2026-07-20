import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from '../test-utils';
import LessonForm from '../../../platform/course/components/LessonForm.jsx';

vi.mock('../../render.jsx');

const hintText = 'Tip: select a paragraph above, then choose "Edit with AI" to have it rewritten.';

const baseAppContext = {
  localeMessages: {
    ai_edit_hint: hintText,
    back: 'Back',
    save_lesson: 'Save',
  },
  aiTextEditModel: 'gpt-4o-mini',
  availableFeatures: ['ai_edit'],
};

function renderLessonForm(appContextOverrides = {}) {
  return renderWithProviders(
    <LessonForm
      header="New Lesson"
      courseId="1"
      cancelCallback={vi.fn()}
      successCallback={vi.fn()}
    />,
    { appContext: { ...baseAppContext, ...appContextOverrides } }
  );
}

describe('LessonForm AI edit hint', () => {
  it('shows the hint when AI edit is enabled and the user can edit', async () => {
    renderLessonForm({ userRole: 'editor' });
    await waitFor(() => expect(screen.getByText(hintText)).toBeInTheDocument());
  });

  it('hides the hint when the AI edit feature is not in availableFeatures', async () => {
    renderLessonForm({ userRole: 'editor', availableFeatures: [] });
    expect(screen.queryByText(hintText)).not.toBeInTheDocument();
  });

  it('hides the hint when no AI text-editing model is configured', async () => {
    renderLessonForm({ userRole: 'editor', aiTextEditModel: null });
    expect(screen.queryByText(hintText)).not.toBeInTheDocument();
  });

  it('hides the hint for a viewer', async () => {
    renderLessonForm({ userRole: 'viewer' });
    expect(screen.queryByText(hintText)).not.toBeInTheDocument();
  });

  it('hides the hint for an instructor (cannot use AI edit either)', async () => {
    renderLessonForm({ userRole: 'instructor' });
    expect(screen.queryByText(hintText)).not.toBeInTheDocument();
  });
});
