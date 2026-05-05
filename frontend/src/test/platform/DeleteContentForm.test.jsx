import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import DeleteContentForm from '../../../platform/course/components/DeleteContentForm';

vi.mock('../../render.jsx');

const localeMessages = {
  delete_content_confirmation: 'Are you sure you want to delete "CONTENT_TITLE"?',
  delete: 'Delete',
  cancel: 'Cancel',
};

const defaultProps = {
  content: { id: 42, title: 'Intro Lesson' },
  onDelete: vi.fn(),
  onCancel: vi.fn(),
};

describe('DeleteContentForm', () => {
  it('renders the confirmation message with the content title', () => {
    renderWithProviders(<DeleteContentForm {...defaultProps} />, {
      appContext: { localeMessages },
    });
    expect(
      screen.getByText('Are you sure you want to delete "Intro Lesson"?')
    ).toBeInTheDocument();
  });

  it('calls onDelete with the content id when delete button is clicked', async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    renderWithProviders(
      <DeleteContentForm {...defaultProps} onDelete={onDelete} />,
      { appContext: { localeMessages } }
    );
    await user.click(screen.getByRole('button', { name: 'Delete' }));
    expect(onDelete).toHaveBeenCalledWith(42);
  });

  it('calls onCancel when the cancel button is clicked', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    renderWithProviders(
      <DeleteContentForm {...defaultProps} onCancel={onCancel} />,
      { appContext: { localeMessages } }
    );
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onCancel).toHaveBeenCalled();
  });
});
