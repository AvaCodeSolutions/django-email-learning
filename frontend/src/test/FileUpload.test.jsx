import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from './test-utils';
import FileUpload from '../components/FileUpload';

const defaultProps = {
  uploadApiEndpoint: '/api/upload/',
  token: 'test-token',
  csrfToken: 'csrf-token',
  onUploadSuccess: vi.fn(),
  onUploadError: vi.fn(),
};

describe('FileUpload', () => {
  beforeEach(() => {
    defaultProps.onUploadSuccess.mockClear();
    defaultProps.onUploadError.mockClear();
  });

  it('renders the upload button with the default label', () => {
    renderWithProviders(<FileUpload {...defaultProps} />);
    expect(screen.getByText('Upload File')).toBeInTheDocument();
  });

  it('renders a custom upload label', () => {
    renderWithProviders(<FileUpload {...defaultProps} uploadLabel="Attach Document" />);
    expect(screen.getByText('Attach Document')).toBeInTheDocument();
  });

  it('renders helper text when provided', () => {
    renderWithProviders(<FileUpload {...defaultProps} helperText="Max size 5 MB" />);
    expect(screen.getByText('Max size 5 MB')).toBeInTheDocument();
  });

  it('shows "Uploading…" while the request is in-flight', async () => {
    let resolveUpload;
    global.fetch.mockReturnValue(
      new Promise((resolve) => {
        resolveUpload = resolve;
      })
    );
    const { container } = renderWithProviders(<FileUpload {...defaultProps} />);
    const input = container.querySelector('input[type="file"]');
    fireEvent.change(input, { target: { files: [new File(['x'], 'doc.pdf', { type: 'application/pdf' })] } });

    await waitFor(() => expect(screen.getByText('Uploading...')).toBeInTheDocument());

    // Settle the promise so act() can clean up
    resolveUpload({ ok: true, json: () => Promise.resolve({ file_name: 'doc.pdf' }) });
  });

  it('shows the filename and remove button after a successful upload', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ file_name: 'report.pdf' }),
    });
    const onUploadSuccess = vi.fn();
    const { container } = renderWithProviders(
      <FileUpload {...defaultProps} onUploadSuccess={onUploadSuccess} />
    );
    fireEvent.change(container.querySelector('input[type="file"]'), {
      target: { files: [new File(['x'], 'report.pdf', { type: 'application/pdf' })] },
    });

    await waitFor(() => expect(screen.getByText('report.pdf')).toBeInTheDocument());
    expect(screen.getByText('Remove File')).toBeInTheDocument();
    expect(onUploadSuccess).toHaveBeenCalledWith({ file_name: 'report.pdf' });
  });

  it('uses a custom remove label', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ file_name: 'doc.pdf' }),
    });
    const { container } = renderWithProviders(
      <FileUpload {...defaultProps} removeLabel="Delete attachment" />
    );
    fireEvent.change(container.querySelector('input[type="file"]'), {
      target: { files: [new File(['x'], 'doc.pdf', { type: 'application/pdf' })] },
    });

    await waitFor(() => expect(screen.getByText('Delete attachment')).toBeInTheDocument());
  });

  it('shows an error alert when the upload fails', async () => {
    global.fetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'File too large' }),
    });
    const { container } = renderWithProviders(<FileUpload {...defaultProps} />);
    fireEvent.change(container.querySelector('input[type="file"]'), {
      target: { files: [new File(['x'], 'big.pdf', { type: 'application/pdf' })] },
    });

    await waitFor(() => expect(screen.getByText('File too large')).toBeInTheDocument());
  });

  it('clears the uploaded file when remove is clicked', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ file_name: 'doc.pdf' }),
    });
    const onUploadSuccess = vi.fn();
    const { container } = renderWithProviders(
      <FileUpload {...defaultProps} onUploadSuccess={onUploadSuccess} />
    );
    fireEvent.change(container.querySelector('input[type="file"]'), {
      target: { files: [new File(['x'], 'doc.pdf', { type: 'application/pdf' })] },
    });

    await waitFor(() => expect(screen.getByText('doc.pdf')).toBeInTheDocument());

    fireEvent.click(screen.getByText('Remove File'));

    expect(screen.queryByText('doc.pdf')).not.toBeInTheDocument();
    expect(onUploadSuccess).toHaveBeenLastCalledWith({ file_path: null, file_name: null });
  });

  it('sends the CSRF token and bearer token in the request', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ file_name: 'f.pdf' }),
    });
    const { container } = renderWithProviders(<FileUpload {...defaultProps} />);
    fireEvent.change(container.querySelector('input[type="file"]'), {
      target: { files: [new File(['x'], 'f.pdf', { type: 'application/pdf' })] },
    });

    await waitFor(() => expect(global.fetch).toHaveBeenCalledOnce());
    const [url, options] = global.fetch.mock.calls[0];
    expect(url).toBe('/api/upload/');
    expect(options.headers['X-CSRFToken']).toBe('csrf-token');
    expect(options.method).toBe('POST');
  });
});
