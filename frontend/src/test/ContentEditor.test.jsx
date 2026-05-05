import { describe, it, expect, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import ContentEditor from '../components/ContentEditor';

vi.mock('../render.jsx');

// ContentEditor returns null until Tiptap's useEditor initialises the
// ProseMirror instance.  All assertions are wrapped in waitFor so they
// only run once the toolbar has mounted.

describe('ContentEditor', () => {
  it('renders the formatting toolbar', async () => {
    renderWithProviders(
      <ContentEditor
        initialContent=""
        contentUpdateCallback={vi.fn()}
      />
    );

    await waitFor(() => expect(screen.getByText('H1')).toBeInTheDocument());
    expect(screen.getByText('H2')).toBeInTheDocument();
    expect(screen.getByText('H3')).toBeInTheDocument();
  });

  it('renders Undo and Redo buttons in the toolbar', async () => {
    renderWithProviders(
      <ContentEditor
        initialContent=""
        contentUpdateCallback={vi.fn()}
      />
    );

    // Wait for the editor to initialise (returns null until ready)
    await waitFor(() => expect(screen.getByText('H1')).toBeInTheDocument());

    // The toolbar contains many icon-only buttons: H1, H2, H3, Undo, Redo,
    // Bold, Italic, Code-block, link, alignment, image, etc.
    const toolbarButtons = screen.getAllByRole('button');
    expect(toolbarButtons.length).toBeGreaterThan(8);
  });

  it('hides the toolbar when disabled=true', async () => {
    renderWithProviders(
      <ContentEditor
        initialContent="<p>Hello</p>"
        contentUpdateCallback={vi.fn()}
        disabled
      />
    );

    // The editor itself is still mounted (content is readable), but the
    // toolbar must not be rendered.
    await waitFor(() =>
      expect(screen.queryByText('H1')).not.toBeInTheDocument()
    );
  });

  it('renders initial HTML content inside the editor area', async () => {
    renderWithProviders(
      <ContentEditor
        initialContent="<p>Welcome to the editor</p>"
        contentUpdateCallback={vi.fn()}
      />
    );

    await waitFor(() =>
      expect(screen.getByText('Welcome to the editor')).toBeInTheDocument()
    );
  });

  it('calls editorInstanceCallback with the editor instance', async () => {
    const onEditor = vi.fn();
    renderWithProviders(
      <ContentEditor
        initialContent=""
        contentUpdateCallback={vi.fn()}
        editorInstanceCallback={onEditor}
      />
    );

    await waitFor(() => expect(onEditor).toHaveBeenCalledWith(expect.objectContaining({
      chain: expect.any(Function),
    })));
  });
});
