import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import ImageUpload from '../components/ImageUpload';

vi.mock('../render.jsx');

describe('ImageUpload', () => {
  beforeEach(() => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ file_url: '/media/img.png', file_path: 'img.png' }),
    });
  });

  it('shows the upload button when no initialUrl is given', () => {
    renderWithProviders(
      <ImageUpload onUploadSuccess={vi.fn()} onUploadError={vi.fn()} initialUrl={null} />
    );
    expect(screen.getByText('Upload')).toBeInTheDocument();
  });

  it('shows the uploaded image when initialUrl is provided', () => {
    renderWithProviders(
      <ImageUpload
        onUploadSuccess={vi.fn()}
        onUploadError={vi.fn()}
        initialUrl="https://example.com/photo.png"
      />
    );
    expect(screen.getByAltText('Uploaded image')).toHaveAttribute(
      'src',
      'https://example.com/photo.png'
    );
  });

  it('shows the remove button when an image is displayed', () => {
    renderWithProviders(
      <ImageUpload
        onUploadSuccess={vi.fn()}
        onUploadError={vi.fn()}
        initialUrl="https://example.com/photo.png"
      />
    );
    expect(screen.getByText('Remove')).toBeInTheDocument();
  });

  it('removes the image when the remove button is clicked', () => {
    const onUploadSuccess = vi.fn();
    renderWithProviders(
      <ImageUpload
        onUploadSuccess={onUploadSuccess}
        onUploadError={vi.fn()}
        initialUrl="https://example.com/photo.png"
      />
    );
    fireEvent.click(screen.getByText('Remove'));
    expect(screen.queryByAltText('Uploaded image')).not.toBeInTheDocument();
    expect(onUploadSuccess).toHaveBeenCalledWith({ file_url: null, file_path: null });
  });

  it('rejects WebP files and calls onUploadError', () => {
    const onUploadError = vi.fn();
    const { container } = renderWithProviders(
      <ImageUpload onUploadSuccess={vi.fn()} onUploadError={onUploadError} initialUrl={null} />
    );
    fireEvent.change(container.querySelector('input[type="file"]'), {
      target: { files: [new File(['data'], 'photo.webp', { type: 'image/webp' })] },
    });
    expect(onUploadError).toHaveBeenCalledWith(expect.any(Error));
    expect(onUploadError.mock.calls[0][0].message).toMatch(/webp/i);
  });

  it('rejects non-image files and calls onUploadError', () => {
    const onUploadError = vi.fn();
    const { container } = renderWithProviders(
      <ImageUpload onUploadSuccess={vi.fn()} onUploadError={onUploadError} initialUrl={null} />
    );
    fireEvent.change(container.querySelector('input[type="file"]'), {
      target: { files: [new File(['data'], 'document.pdf', { type: 'application/pdf' })] },
    });
    expect(onUploadError).toHaveBeenCalledWith(expect.any(Error));
  });

  it('uploads a valid image and shows the result', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ file_url: '/media/img.png', file_path: 'img.png' }),
    });
    const onUploadSuccess = vi.fn();
    const { container } = renderWithProviders(
      <ImageUpload organizationId={42} onUploadSuccess={onUploadSuccess} onUploadError={vi.fn()} initialUrl={null} />
    );
    fireEvent.change(container.querySelector('input[type="file"]'), {
      target: { files: [new File(['data'], 'photo.png', { type: 'image/png' })] },
    });

    await waitFor(() =>
      expect(onUploadSuccess).toHaveBeenCalledWith({
        file_url: '/media/img.png',
        file_path: 'img.png',
      })
    );
    expect(screen.getByAltText('Uploaded image')).toHaveAttribute('src', '/media/img.png');
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/organizations/42/files/'),
      expect.any(Object)
    );
  });

  it('calls onUploadError when the server returns an error response', async () => {
    global.fetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) });
    const onUploadError = vi.fn();
    const { container } = renderWithProviders(
      <ImageUpload onUploadSuccess={vi.fn()} onUploadError={onUploadError} initialUrl={null} />
    );
    fireEvent.change(container.querySelector('input[type="file"]'), {
      target: { files: [new File(['data'], 'photo.png', { type: 'image/png' })] },
    });

    await waitFor(() => expect(onUploadError).toHaveBeenCalledWith(expect.any(Error)));
  });

  it('updates the preview when initialUrl prop changes', async () => {
    const { rerender } = renderWithProviders(
      <ImageUpload
        onUploadSuccess={vi.fn()}
        onUploadError={vi.fn()}
        initialUrl="https://example.com/old.png"
      />
    );
    expect(screen.getByAltText('Uploaded image')).toHaveAttribute('src', 'https://example.com/old.png');

    rerender(
      <ImageUpload
        onUploadSuccess={vi.fn()}
        onUploadError={vi.fn()}
        initialUrl="https://example.com/new.png"
      />
    );
    // Rerender without providers — need to re-wrap; verify new URL is reflected
    await waitFor(() =>
      expect(screen.getByAltText('Uploaded image')).toHaveAttribute(
        'src',
        'https://example.com/new.png'
      )
    );
  });
});
