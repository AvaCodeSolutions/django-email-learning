import { describe, it, expect, beforeEach, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import Organization from '../../../platform/organization/Organization';

vi.mock('../../render.jsx');

const localeMessages = {
  organizations: 'Organizations',
  general_info: 'General Info',
  members: 'Members',
  edit: 'Edit',
  name: 'Name',
  description: 'Description',
  organization_is_public: 'Public organization',
  organization_is_public_helper_text: 'When enabled, this organization is publicly visible.',
  cancel: 'Cancel',
  update: 'Update',
  name_required: 'Name is required.',
  description_required: 'Description is required.',
  error_try_again: 'An error occurred. Please try again.',
  logo_upload_failed: 'Logo upload failed.',
  upload_button_label: 'Upload',
  organization_logo_alt: 'Organization Logo',
  remove_image: 'Remove',
  website: 'Website',
  linkedin_page: 'LinkedIn page',
  youtube_channel: 'YouTube channel',
  facebook_page: 'Facebook page',
  instagram: 'Instagram',
  tiktok: 'TikTok',
  twitter_x: 'X (Twitter)',
  whatsapp_channel: 'WhatsApp channel',
  telegram_channel: 'Telegram channel',
  substack: 'Substack',
  invalid_url_helper_text: 'Enter a valid URL starting with http:// or https://',
  social_links: 'Social links',
  add_social_link: 'Add link',
  social_link_platform: 'Platform',
  social_link_url: 'URL',
  remove_social_link: 'Remove link',
  no_users_in_organization: 'No users in this organization yet.',
  add_user: 'Add User',
  user: 'User',
  role: 'Role',
  actions: 'Actions',
  cannot_add_member: 'Adding new members is not allowed.',
};

const organization = {
  id: 1,
  name: 'Acme Corp',
  description: 'A great company.',
  logo: null,
  logo_path: null,
  social_links: [],
  is_public: true,
};

const baseAppContext = {
  organizationId: '1',
  localeMessages,
};

describe('Organization', () => {
  beforeEach(() => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/users/')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ organization_users: [] }) });
      }
      if (url.endsWith('/organizations/1/')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(organization) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  const openGeneralInfoTab = async (user) => {
    await user.click(await screen.findByRole('tab', { name: /General Info/i }));
  };

  it('renders the General Info tab fields disabled by default', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Organization />, {
      appContext: { ...baseAppContext, isOrganizationAdmin: true },
    });
    await openGeneralInfoTab(user);

    await waitFor(() => expect(screen.getByLabelText(/Name/)).toHaveValue('Acme Corp'));
    expect(screen.getByLabelText(/Name/)).toBeDisabled();
    expect(screen.getByLabelText(/Description/)).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Update' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancel' })).not.toBeInTheDocument();
  });

  it('shows the edit icon for an organization admin and toggles the form editable', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Organization />, {
      appContext: { ...baseAppContext, isOrganizationAdmin: true },
    });
    await openGeneralInfoTab(user);
    await waitFor(() => expect(screen.getByLabelText(/Name/)).toHaveValue('Acme Corp'));

    await user.click(screen.getByRole('button', { name: 'Edit' }));

    expect(screen.getByLabelText(/Name/)).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Update' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument();
  });

  it('hides the edit icon and keeps fields disabled for a non-admin', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Organization />, {
      appContext: { ...baseAppContext, isOrganizationAdmin: false, isPlatformAdmin: false },
    });
    await openGeneralInfoTab(user);
    await waitFor(() => expect(screen.getByLabelText(/Name/)).toHaveValue('Acme Corp'));

    expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Name/)).toBeDisabled();
  });

  it('discards unsaved edits and returns to read-only when Cancel is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Organization />, {
      appContext: { ...baseAppContext, isOrganizationAdmin: true },
    });
    await openGeneralInfoTab(user);
    await waitFor(() => expect(screen.getByLabelText(/Name/)).toHaveValue('Acme Corp'));

    await user.click(screen.getByRole('button', { name: 'Edit' }));
    await user.clear(screen.getByLabelText(/Name/));
    await user.type(screen.getByLabelText(/Name/), 'Changed Name');
    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(screen.getByLabelText(/Name/)).toHaveValue('Acme Corp');
    expect(screen.getByLabelText(/Name/)).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument();
  });

  it('saves the edited organization and returns to read-only on success', async () => {
    const updatedOrganization = { ...organization, name: 'Acme Corp Updated' };
    global.fetch.mockImplementation((url, options) => {
      if (options?.method === 'POST' && url.endsWith('/organizations/1/')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(updatedOrganization) });
      }
      if (url.includes('/users/')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ organization_users: [] }) });
      }
      if (url.endsWith('/organizations/1/')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(organization) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });

    const user = userEvent.setup();
    renderWithProviders(<Organization />, {
      appContext: { ...baseAppContext, isOrganizationAdmin: true },
    });
    await openGeneralInfoTab(user);
    await waitFor(() => expect(screen.getByLabelText(/Name/)).toHaveValue('Acme Corp'));

    await user.click(screen.getByRole('button', { name: 'Edit' }));
    await user.clear(screen.getByLabelText(/Name/));
    await user.type(screen.getByLabelText(/Name/), 'Acme Corp Updated');
    await user.click(screen.getByRole('button', { name: 'Update' }));

    await waitFor(() => expect(screen.getByLabelText(/Name/)).toHaveValue('Acme Corp Updated'));
    expect(screen.getByLabelText(/Name/)).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument();
  });
});
