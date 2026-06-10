import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import Button from '@mui/material/Button';
import EmptyTableState from '../components/EmptyTableState';

function renderInTable(ui) {
  return renderWithProviders(
    <Table>
      <TableBody>{ui}</TableBody>
    </Table>
  );
}

describe('EmptyTableState', () => {
  it('renders the message', () => {
    renderInTable(<EmptyTableState colSpan={3} message="No items found." />);
    expect(screen.getByText('No items found.')).toBeInTheDocument();
  });

  it('renders the inbox icon', () => {
    renderInTable(<EmptyTableState colSpan={3} message="Empty" />);
    // MUI icons render an <svg> — verify it's present via role or data-testid fallback
    expect(document.querySelector('svg')).toBeTruthy();
  });

  it('renders an optional action element', () => {
    renderInTable(
      <EmptyTableState
        colSpan={3}
        message="No courses."
        action={<Button>Add course</Button>}
      />
    );
    expect(screen.getByRole('button', { name: 'Add course' })).toBeInTheDocument();
  });

  it('does not render an action when none is provided', () => {
    renderInTable(<EmptyTableState colSpan={3} message="Empty" />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});
