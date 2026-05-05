import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import CreateImapForm from '../../../platform/courses/components/CreateImapForm';

vi.mock('../../render.jsx');

const localeMessages = {
  email: 'Email',
  password: 'Password',
  server: 'Server',
  port: 'Port',
  add: 'Add',
  add_folder_helper_text: 'Enter folder name and press Enter or click Add.',
  email_required_helper_text: 'Email is required.',
  invalid_email_helper_text: 'Invalid email address.',
  password_required_helper_text: 'Password is required.',
  server_required_helper_text: 'Server is required.',
  port_required_helper_text: 'Port is required.',
  invalid_port_helper_text: 'Invalid port number.',
};

describe('CreateImapForm', () => {
  it('renders all required fields', () => {
    renderWithProviders(<CreateImapForm onSuccess={vi.fn()} activeOrganizationId="1" />, {
      appContext: { localeMessages },
    });
    expect(screen.getByLabelText(/Email/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Server/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Port/)).toBeInTheDocument();
  });

  it('shows the inbox folder chip by default', () => {
    renderWithProviders(<CreateImapForm onSuccess={vi.fn()} activeOrganizationId="1" />, {
      appContext: { localeMessages },
    });
    expect(screen.getByText('inbox')).toBeInTheDocument();
  });

  it('shows validation errors when submitted with empty fields', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CreateImapForm onSuccess={vi.fn()} activeOrganizationId="1" />, {
      appContext: { localeMessages },
    });
    await user.click(screen.getAllByRole('button', { name: 'Add' })[1]); // submit button
    await waitFor(() => {
      expect(screen.getByText('Email is required.')).toBeInTheDocument();
      expect(screen.getByText('Password is required.')).toBeInTheDocument();
      expect(screen.getByText('Server is required.')).toBeInTheDocument();
      expect(screen.getByText('Port is required.')).toBeInTheDocument();
    });
  });

  it('shows invalid email error for bad email format', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CreateImapForm onSuccess={vi.fn()} activeOrganizationId="1" />, {
      appContext: { localeMessages },
    });
    await user.type(screen.getByLabelText(/Email/), 'not-an-email');
    await user.click(screen.getAllByRole('button', { name: 'Add' })[1]);
    await waitFor(() => {
      expect(screen.getByText('Invalid email address.')).toBeInTheDocument();
    });
  });

  it('adds a new folder chip when folder name is entered and Add is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<CreateImapForm onSuccess={vi.fn()} activeOrganizationId="1" />, {
      appContext: { localeMessages },
    });
    await user.type(screen.getByLabelText('Add folder'), 'sent');
    await user.click(screen.getAllByRole('button', { name: 'Add' })[0]);
    expect(screen.getByText('sent')).toBeInTheDocument();
  });

  it('calls onSuccess after successful submission', async () => {
    const onSuccess = vi.fn();
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: '10', email: 'imap@example.com' }),
    });
    const user = userEvent.setup();
    renderWithProviders(<CreateImapForm onSuccess={onSuccess} activeOrganizationId="1" />, {
      appContext: { localeMessages },
    });
    await user.type(screen.getByLabelText(/Email/), 'imap@example.com');
    await user.type(screen.getByLabelText(/Password/), 'secret');
    await user.type(screen.getByLabelText(/Server/), 'imap.example.com');
    await user.type(screen.getByLabelText(/Port/), '993');
    await user.click(screen.getAllByRole('button', { name: 'Add' })[1]);
    await waitFor(() =>
      expect(onSuccess).toHaveBeenCalledWith({ id: '10', email: 'imap@example.com' })
    );
  });
});
