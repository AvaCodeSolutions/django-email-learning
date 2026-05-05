import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import RequiredTextField from '../components/RequiredTextField';

vi.mock('../render.jsx');

describe('RequiredTextField', () => {
  it('renders the label text', () => {
    renderWithProviders(<RequiredTextField label="Email" value="" onChange={vi.fn()} />);
    // getByLabelText finds the input whose label matches — confirms the label is rendered
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  });

  it('marks the input as required', () => {
    renderWithProviders(<RequiredTextField label="Name" value="" onChange={vi.fn()} />);
    expect(screen.getByRole('textbox')).toBeRequired();
  });

  it('renders helper text', () => {
    renderWithProviders(
      <RequiredTextField label="Name" value="" onChange={vi.fn()} helperText="Enter full name" />
    );
    expect(screen.getByText('Enter full name')).toBeInTheDocument();
  });

  it('renders in error state with aria-invalid and helper text', () => {
    renderWithProviders(
      <RequiredTextField label="Name" value="" onChange={vi.fn()} error helperText="This field is required" />
    );
    expect(screen.getByRole('textbox')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText('This field is required')).toBeInTheDocument();
  });

  it('fires onChange when user types', () => {
    const onChange = vi.fn();
    renderWithProviders(<RequiredTextField label="Name" value="" onChange={onChange} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Jane' } });
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it('applies dir="rtl" when context direction is rtl', () => {
    const { container } = renderWithProviders(
      <RequiredTextField label="Name" value="" onChange={vi.fn()} />,
      { appContext: { direction: 'rtl' } }
    );
    expect(container.querySelector('[dir="rtl"]')).toBeInTheDocument();
  });

  it('passes extra sx and props through to TextField', () => {
    renderWithProviders(
      <RequiredTextField
        label="Username"
        value="alice"
        onChange={vi.fn()}
        inputProps={{ 'data-testid': 'user-input' }}
      />
    );
    expect(screen.getByTestId('user-input')).toBeInTheDocument();
  });
});
