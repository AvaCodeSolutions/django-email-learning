import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import OrganizationForm from '../../../platform/organizations/components/OrganizationForm';

vi.mock('../../render.jsx');

const localeMessages = {
  name: 'Name',
  description: 'Description',
  organization_is_public: 'Public organization',
  organization_is_public_helper_text: 'When enabled, this organization is publicly visible.',
  cancel: 'Cancel',
  create: 'Create',
  update: 'Update',
  name_required: 'Name is required.',
  description_required: 'Description is required.',
  error_try_again: 'An error occurred. Please try again.',
  logo_upload_failed: 'Logo upload failed.',
  upload_button_label: 'Upload',
  uploaded_image_alt: 'Uploaded image',
  remove_image: 'Remove',
  website: 'Website',
  linkedin_page: 'LinkedIn page',
  youtube_channel: 'YouTube channel',
  invalid_url_helper_text: 'Enter a valid URL starting with http:// or https://',
  social_links: 'Social links',
  add_social_link: 'Add link',
  social_link_platform: 'Platform',
  social_link_url: 'URL',
  remove_social_link: 'Remove link',
};

const createProps = {
  successCallback: vi.fn(),
  failureCallback: vi.fn(),
  cancelCallback: vi.fn(),
  createMode: true,
};

describe('OrganizationForm', () => {
  beforeEach(() => {
    createProps.successCallback.mockClear();
    createProps.failureCallback.mockClear();
    createProps.cancelCallback.mockClear();
  });

  it('renders name and description fields', () => {
    renderWithProviders(<OrganizationForm {...createProps} />, {
      appContext: { localeMessages },
    });
    expect(screen.getByLabelText(/Name/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Description/)).toBeInTheDocument();
  });

  it('shows Create button in create mode', () => {
    renderWithProviders(<OrganizationForm {...createProps} />, {
      appContext: { localeMessages },
    });
    expect(screen.getByRole('button', { name: 'Create' })).toBeInTheDocument();
  });

  it('shows Update button in edit mode', () => {
    renderWithProviders(
      <OrganizationForm {...createProps} createMode={false} organizationId="1" />,
      { appContext: { localeMessages } }
    );
    expect(screen.getByRole('button', { name: 'Update' })).toBeInTheDocument();
  });

  it('shows validation errors when name and description are empty', async () => {
    const user = userEvent.setup();
    renderWithProviders(<OrganizationForm {...createProps} />, {
      appContext: { localeMessages },
    });
    await user.click(screen.getByRole('button', { name: 'Create' }));
    await waitFor(() => {
      expect(screen.getByText('Name is required.')).toBeInTheDocument();
      expect(screen.getByText('Description is required.')).toBeInTheDocument();
    });
  });

  it('shows URL validation error for invalid social link URL', async () => {
    const user = userEvent.setup();
    renderWithProviders(<OrganizationForm {...createProps} />, {
      appContext: { localeMessages },
    });
    await user.click(screen.getByRole('button', { name: 'Add link' }));
    await user.type(screen.getByLabelText('URL'), 'not-a-url');
    await user.click(screen.getByRole('button', { name: 'Create' }));
    await waitFor(() => {
      expect(
        screen.getByText('Enter a valid URL starting with http:// or https://')
      ).toBeInTheDocument();
    });
  });

  it('adds a social link and submits it with the form', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: '1', name: 'Acme Corp' }),
    });
    const user = userEvent.setup();
    renderWithProviders(<OrganizationForm {...createProps} />, {
      appContext: { localeMessages },
    });
    await user.type(screen.getByLabelText(/Name/), 'Acme Corp');
    await user.type(screen.getByLabelText(/Description/), 'A great company.');
    await user.click(screen.getByRole('button', { name: 'Add link' }));
    await user.type(screen.getByLabelText('URL'), 'https://acme.example.com');
    await user.click(screen.getByRole('button', { name: 'Create' }));

    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    const [, options] = global.fetch.mock.calls.at(-1);
    expect(JSON.parse(options.body)).toMatchObject({
      social_links: [{ platform: 'website', url: 'https://acme.example.com' }],
    });
  });

  it('calls cancelCallback when cancel button is clicked', async () => {
    const user = userEvent.setup();
    const cancelCallback = vi.fn();
    renderWithProviders(
      <OrganizationForm {...createProps} cancelCallback={cancelCallback} />,
      { appContext: { localeMessages } }
    );
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(cancelCallback).toHaveBeenCalled();
  });

  it('submits the form and calls successCallback on success', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: '1', name: 'Acme Corp' }),
    });
    const user = userEvent.setup();
    const successCallback = vi.fn();
    renderWithProviders(
      <OrganizationForm {...createProps} successCallback={successCallback} />,
      { appContext: { localeMessages } }
    );
    await user.type(screen.getByLabelText(/Name/), 'Acme Corp');
    await user.type(screen.getByLabelText(/Description/), 'A great company.');
    await user.click(screen.getByRole('button', { name: 'Create' }));
    await waitFor(() =>
      expect(successCallback).toHaveBeenCalledWith({ id: '1', name: 'Acme Corp' })
    );
  });

  it('sends remove_logo when an existing logo is removed and the form is saved', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: '1', name: 'Acme Corp' }),
    });
    const user = userEvent.setup();
    renderWithProviders(
      <OrganizationForm
        {...createProps}
        createMode={false}
        organizationId="1"
        initialName="Acme Corp"
        initialDescription="A great company."
        initialLogoUrl="https://example.com/logo.png"
      />,
      { appContext: { localeMessages } }
    );
    await user.click(screen.getByRole('button', { name: 'Remove' }));
    await user.click(screen.getByRole('button', { name: 'Update' }));

    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    const [, options] = global.fetch.mock.calls.at(-1);
    expect(JSON.parse(options.body)).toMatchObject({ remove_logo: true });
  });
});
