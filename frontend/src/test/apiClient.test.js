import { describe, it, expect, vi, beforeEach } from 'vitest';
import apiClient from '../apiClient.js';

vi.mock('../utils.js', () => ({
  getCookie: vi.fn(() => 'test-csrf-token'),
}));

function mockFetch(status, body) {
  global.fetch = vi.fn(() =>
    Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(body),
    })
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('apiClient.get', () => {
  it('sends a GET request with CSRF token and JSON content type', async () => {
    mockFetch(200, { items: [] });

    await apiClient.get('/api/courses/');

    expect(fetch).toHaveBeenCalledWith('/api/courses/', expect.objectContaining({
      method: 'GET',
      headers: expect.objectContaining({
        'X-CSRFToken': 'test-csrf-token',
        'Content-Type': 'application/json',
      }),
      credentials: 'include',
    }));
  });

  it('returns parsed JSON on success', async () => {
    mockFetch(200, { items: [1, 2] });
    const result = await apiClient.get('/api/courses/');
    expect(result).toEqual({ items: [1, 2] });
  });

  it('throws ApiError on non-2xx response', async () => {
    mockFetch(404, { detail: 'Not found' });
    await expect(apiClient.get('/api/courses/')).rejects.toThrow(apiClient.ApiError);
  });

  it('throws ApiError with correct status', async () => {
    mockFetch(403, { error: 'Forbidden' });
    try {
      await apiClient.get('/api/courses/');
    } catch (e) {
      expect(e.status).toBe(403);
      expect(e.body).toEqual({ error: 'Forbidden' });
    }
  });
});

describe('apiClient.post', () => {
  it('sends a POST with JSON-serialised body', async () => {
    mockFetch(201, { id: 1 });

    await apiClient.post('/api/courses/', { title: 'Test' });

    expect(fetch).toHaveBeenCalledWith('/api/courses/', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ title: 'Test' }),
      headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
    }));
  });
});

describe('apiClient.del', () => {
  it('sends a DELETE request', async () => {
    mockFetch(204, null);
    global.fetch = vi.fn(() =>
      Promise.resolve({ ok: true, status: 204, json: () => Promise.resolve(null) })
    );

    const result = await apiClient.del('/api/courses/1/');

    expect(fetch).toHaveBeenCalledWith('/api/courses/1/', expect.objectContaining({
      method: 'DELETE',
    }));
    expect(result).toBeNull();
  });
});

describe('apiClient.upload', () => {
  it('omits Content-Type so the browser sets the multipart boundary', async () => {
    mockFetch(200, { url: '/files/x.pdf' });
    const formData = new FormData();

    await apiClient.upload('/api/file/', formData);

    const [, options] = fetch.mock.calls[0];
    expect(options.headers['Content-Type']).toBeUndefined();
    expect(options.body).toBe(formData);
  });
});
