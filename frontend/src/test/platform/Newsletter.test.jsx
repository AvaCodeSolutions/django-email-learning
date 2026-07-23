import { describe, it, expect, beforeEach, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import Newsletter from '../../../platform/newsletter/Newsletter';

vi.mock('../../render.jsx');
vi.mock('vite/modulepreload-polyfill', () => ({}));
vi.mock('@melloware/coloris', () => {
  const coloris = vi.fn();
  coloris.init = vi.fn();
  return { default: coloris };
});

const localeMessages = {
  scheduled: 'Scheduled',
  sent: 'Sent',
  all: 'All',
  no_sendouts: 'No sendouts yet.',
  create_sendout: 'Create Sendout',
  newsletter_subscribers: 'Subscribers',
  add_to_your_site: 'Add to your site',
  embed_customize_form_title: 'Customize your form',
  embed_preview_title: 'Preview',
  embed_button_bg_color_label: 'Button background',
  embed_button_text_color_label: 'Button text color',
  embed_code_dialog_title: 'Embed on your site',
  embed_code_dialog_description: 'Paste this snippet into your own website.',
  embed_code_loading: 'Loading embed code...',
  embed_code_error: "Couldn't load the embed code. Please try again.",
  copy_embed_script: 'Copy script',
  copy_embed_widget: 'Copy widget tag',
  embed_code_copied: 'Copied!',
  close: 'Close',
};

const baseAppContext = {
  newsletterId: '3',
  newsletterTitle: 'Weekly Digest',
  organizationId: '1',
  isOrganizationAdmin: true,
  localeMessages,
};

describe('Newsletter', () => {
  beforeEach(() => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/sendouts')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve({ sendouts: [] }) });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
  });

  describe('"Add to your site" embed button', () => {
    it('is hidden when embeddable enrollment is disabled', () => {
      renderWithProviders(<Newsletter />, {
        appContext: { ...baseAppContext, embeddableEnrollmentEnabled: false },
      });
      expect(screen.queryByRole('button', { name: 'Add to your site' })).not.toBeInTheDocument();
    });

    it('is shown when embeddable enrollment is enabled', () => {
      renderWithProviders(<Newsletter />, {
        appContext: { ...baseAppContext, embeddableEnrollmentEnabled: true },
      });
      expect(screen.getByRole('button', { name: 'Add to your site' })).toBeInTheDocument();
    });

    it('fetches and displays the embed snippet on click', async () => {
      const user = userEvent.setup();
      global.fetch.mockImplementation((url) => {
        if (url.includes('/embed_snippet/')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                script_html: '<script src="https://example.com/embed/del-enroll-form.js"></script>',
                widget_html: '<del-newsletter-form token="tok" newsletter_id="3"></del-newsletter-form>',
              }),
          });
        }
        if (url.includes('/sendouts')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve({ sendouts: [] }) });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });
      renderWithProviders(<Newsletter />, {
        appContext: { ...baseAppContext, embeddableEnrollmentEnabled: true },
      });

      await user.click(screen.getByRole('button', { name: 'Add to your site' }));

      expect(
        await screen.findByText('<script src="https://example.com/embed/del-enroll-form.js"></script>')
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          '<del-newsletter-form button_bg_color="#4f46e5" button_text_color="#ffffff" token="tok" newsletter_id="3"></del-newsletter-form>'
        )
      ).toBeInTheDocument();
    });

    it('shows an error message when the embed snippet fails to load', async () => {
      const user = userEvent.setup();
      global.fetch.mockImplementation((url) => {
        if (url.includes('/embed_snippet/')) {
          return Promise.resolve({ ok: false, status: 409, json: () => Promise.resolve({ error: 'nope' }) });
        }
        if (url.includes('/sendouts')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve({ sendouts: [] }) });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });
      renderWithProviders(<Newsletter />, {
        appContext: { ...baseAppContext, embeddableEnrollmentEnabled: true },
      });

      await user.click(screen.getByRole('button', { name: 'Add to your site' }));

      expect(await screen.findByRole('alert')).toHaveTextContent(localeMessages.embed_code_error);
    });

    it('closes the dialog when Close is clicked', async () => {
      const user = userEvent.setup();
      global.fetch.mockImplementation((url) => {
        if (url.includes('/embed_snippet/')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                script_html: '<script src="https://example.com/embed/del-enroll-form.js"></script>',
                widget_html: '<del-newsletter-form token="tok" newsletter_id="3"></del-newsletter-form>',
              }),
          });
        }
        if (url.includes('/sendouts')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve({ sendouts: [] }) });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });
      renderWithProviders(<Newsletter />, {
        appContext: { ...baseAppContext, embeddableEnrollmentEnabled: true },
      });

      await user.click(screen.getByRole('button', { name: 'Add to your site' }));
      await screen.findByText(
        '<del-newsletter-form button_bg_color="#4f46e5" button_text_color="#ffffff" token="tok" newsletter_id="3"></del-newsletter-form>'
      );
      await user.click(screen.getByRole('button', { name: 'Close' }));

      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    });

    it('reflects a custom button background color typed into the color field', async () => {
      const user = userEvent.setup();
      global.fetch.mockImplementation((url) => {
        if (url.includes('/embed_snippet/')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                script_html: '<script src="https://example.com/embed/del-enroll-form.js"></script>',
                widget_html: '<del-newsletter-form token="tok" newsletter_id="3"></del-newsletter-form>',
              }),
          });
        }
        if (url.includes('/sendouts')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve({ sendouts: [] }) });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });
      renderWithProviders(<Newsletter />, {
        appContext: { ...baseAppContext, embeddableEnrollmentEnabled: true },
      });

      await user.click(screen.getByRole('button', { name: 'Add to your site' }));
      await screen.findByText(
        '<del-newsletter-form button_bg_color="#4f46e5" button_text_color="#ffffff" token="tok" newsletter_id="3"></del-newsletter-form>'
      );

      const bgColorField = screen.getByLabelText('Button background');
      await user.clear(bgColorField);
      await user.type(bgColorField, '#16a34a');

      await screen.findByText(
        '<del-newsletter-form button_bg_color="#16a34a" button_text_color="#ffffff" token="tok" newsletter_id="3"></del-newsletter-form>'
      );
    });
  });
});
