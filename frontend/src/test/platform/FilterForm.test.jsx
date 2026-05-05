import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import FilterForm from '../../../platform/courses/components/FilterForm';

vi.mock('../../render.jsx');

const localeMessages = {
  filter: 'Filter',
  course_status: 'Course Status',
  all: 'All',
  enabled: 'Enabled',
  disabled: 'Disabled',
};

describe('FilterForm', () => {
  it('renders the filter heading and course status label', () => {
    renderWithProviders(<FilterForm onStatusChange={vi.fn()} />, {
      appContext: { localeMessages },
    });
    expect(screen.getByText('Filter')).toBeInTheDocument();
    expect(screen.getByText(/Course Status/)).toBeInTheDocument();
  });

  it('renders all three radio options', () => {
    renderWithProviders(<FilterForm onStatusChange={vi.fn()} />, {
      appContext: { localeMessages },
    });
    expect(screen.getByLabelText('All')).toBeInTheDocument();
    expect(screen.getByLabelText('Enabled')).toBeInTheDocument();
    expect(screen.getByLabelText('Disabled')).toBeInTheDocument();
  });

  it('calls onStatusChange with correct query strings when options are selected', async () => {
    const user = userEvent.setup();
    const onStatusChange = vi.fn();
    renderWithProviders(<FilterForm onStatusChange={onStatusChange} />, {
      appContext: { localeMessages },
    });

    await user.click(screen.getByLabelText('Enabled'));
    expect(onStatusChange).toHaveBeenCalledWith('?enabled=true');

    await user.click(screen.getByLabelText('Disabled'));
    expect(onStatusChange).toHaveBeenCalledWith('?enabled=false');

    await user.click(screen.getByLabelText('All'));
    expect(onStatusChange).toHaveBeenCalledWith('');
  });
});
