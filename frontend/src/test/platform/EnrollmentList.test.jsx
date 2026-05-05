import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import EnrollmentList from '../../../platform/learners/components/EnrollmentList';

vi.mock('../../render.jsx');

const localeMessages = {
  nor_enrollments_found: 'No enrollments found.',
  course: 'Course',
  status: 'Status',
  progress: 'Progress',
  certificate: 'Certificate',
};

const sampleEnrollments = [
  {
    id: '1',
    course_title: 'Python Basics',
    status: 'active',
    progress: 40,
    certificate_url: null,
  },
  {
    id: '2',
    course_title: 'React Advanced',
    status: 'completed',
    progress: 100,
    certificate_url: 'https://example.com/cert.pdf',
  },
];

describe('EnrollmentList', () => {
  it('renders empty message when there are no enrollments', () => {
    renderWithProviders(
      <EnrollmentList enrollments={[]} selectHandler={vi.fn()} />,
      { appContext: { localeMessages } }
    );
    expect(screen.getByText('No enrollments found.')).toBeInTheDocument();
  });

  it('renders enrollment rows for each enrollment', () => {
    renderWithProviders(
      <EnrollmentList enrollments={sampleEnrollments} selectHandler={vi.fn()} />,
      { appContext: { localeMessages } }
    );
    expect(screen.getByText('Python Basics')).toBeInTheDocument();
    expect(screen.getByText('React Advanced')).toBeInTheDocument();
  });

  it('renders table headers', () => {
    renderWithProviders(
      <EnrollmentList enrollments={sampleEnrollments} selectHandler={vi.fn()} />,
      { appContext: { localeMessages } }
    );
    expect(screen.getByText('Course')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Progress')).toBeInTheDocument();
  });

  it('calls selectHandler when a row is clicked', async () => {
    const user = userEvent.setup();
    const selectHandler = vi.fn();
    renderWithProviders(
      <EnrollmentList enrollments={sampleEnrollments} selectHandler={selectHandler} />,
      { appContext: { localeMessages } }
    );
    await user.click(screen.getByText('Python Basics'));
    expect(selectHandler).toHaveBeenCalledWith('1');
  });
});
