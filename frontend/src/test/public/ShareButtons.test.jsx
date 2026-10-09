import { afterEach, describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../test-utils';
import ShareButtons from '../../../public/components/ShareButtons';
import { buildShareLinks } from '../../../public/components/shareLinks';

vi.mock('../../render.jsx');

const URL = 'https://example.com/courses/acme/intro?x=1';
const TITLE = 'Intro & Basics';

const renderShare = (props = {}) => renderWithProviders(
    <ShareButtons url={URL} title={TITLE} messages={{}} label="Share this course" {...props} />
);

describe('buildShareLinks', () => {
    it('encodes the url and text into each network link', () => {
        const links = Object.fromEntries(buildShareLinks(URL, TITLE).map((link) => [link.key, link.href]));
        const u = encodeURIComponent(URL);

        expect(links.x).toBe(`https://x.com/intent/post?url=${u}&text=Intro%20%26%20Basics`);
        expect(links.linkedin).toBe(`https://www.linkedin.com/sharing/share-offsite/?url=${u}`);
        expect(links.facebook).toBe(`https://www.facebook.com/sharer/sharer.php?u=${u}`);
        expect(links.whatsapp).toBe(`https://wa.me/?text=${encodeURIComponent(`${TITLE} ${URL}`)}`);
        expect(links.telegram).toBe(`https://t.me/share/url?url=${u}&text=Intro%20%26%20Basics`);
    });
});

describe('ShareButtons', () => {
    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('renders nothing without a url', () => {
        const { container } = renderShare({ url: '' });
        expect(container).toBeEmptyDOMElement();
    });

    it('opens network links in a new tab and uses localized labels', () => {
        renderShare({ messages: { share_on: 'Teilen auf PLATFORM' } });

        const linkedIn = screen.getByRole('link', { name: 'Teilen auf LinkedIn' });
        expect(linkedIn).toHaveAttribute('target', '_blank');
        expect(linkedIn).toHaveAttribute('rel', 'noopener noreferrer');
        expect(screen.getByRole('link', { name: 'Share by email' }))
            .toHaveAttribute('href', `mailto:?subject=${encodeURIComponent(TITLE)}&body=${encodeURIComponent(URL)}`);
        expect(screen.getByText('Share this course')).toBeInTheDocument();
    });

    it('copies the link and confirms it', async () => {
        const user = userEvent.setup();
        const writeText = vi.fn().mockResolvedValue(undefined);
        renderShare();
        // userEvent installs its own clipboard on setup; replace it afterwards.
        Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });

        await user.click(screen.getByRole('button', { name: 'Copy link' }));

        expect(writeText).toHaveBeenCalledWith(URL);
        await waitFor(() => expect(screen.getByRole('button', { name: 'Link copied' })).toBeInTheDocument());
    });

    it('offers the native share sheet when the browser supports it', async () => {
        const share = vi.fn().mockResolvedValue(undefined);
        vi.stubGlobal('navigator', { ...navigator, share, clipboard: navigator.clipboard });
        renderShare();

        await userEvent.click(screen.getByRole('button', { name: 'More options' }));

        expect(share).toHaveBeenCalledWith({ title: TITLE, url: URL });
    });

    it('hides the native share button when unsupported', () => {
        renderShare();
        expect(screen.queryByRole('button', { name: 'More options' })).not.toBeInTheDocument();
    });
});
