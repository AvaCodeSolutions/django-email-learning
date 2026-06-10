import { getCookie } from './utils.js';

/**
 * Thin API client that automatically attaches the Django CSRF token and
 * sets Content-Type: application/json for all JSON requests.
 *
 * Usage:
 *   import apiClient from '../../src/apiClient.js';
 *
 *   // JSON requests
 *   const data = await apiClient.get('/api/organizations/1/courses/');
 *   const created = await apiClient.post('/api/organizations/1/courses/', { title: 'My course' });
 *   const updated = await apiClient.post('/api/organizations/1/courses/1/', { title: 'Updated' });
 *   await apiClient.del('/api/organizations/1/courses/1/');
 *
 *   // Multipart upload (pass a FormData object; Content-Type is omitted so the
 *   // browser sets it with the correct boundary)
 *   const result = await apiClient.upload('/api/organizations/1/file/', formData);
 */

class ApiError extends Error {
  constructor(status, body) {
    super(`API error ${status}`);
    this.status = status;
    this.body = body;
  }
}

async function request(url, { method = 'GET', body, isUpload = false } = {}) {
  const headers = {
    'X-CSRFToken': getCookie('csrftoken'),
  };

  if (!isUpload) {
    headers['Content-Type'] = 'application/json';
  }

  const options = {
    method,
    headers,
    credentials: 'include',
  };

  if (body !== undefined) {
    options.body = isUpload ? body : JSON.stringify(body);
  }

  const response = await fetch(url, options);

  if (!response.ok) {
    let errorBody;
    try {
      errorBody = await response.json();
    } catch {
      errorBody = null;
    }
    throw new ApiError(response.status, errorBody);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

const apiClient = {
  get: (url) => request(url, { method: 'GET' }),
  post: (url, body) => request(url, { method: 'POST', body }),
  del: (url, body) => request(url, { method: 'DELETE', body }),
  upload: (url, formData) => request(url, { method: 'POST', body: formData, isUpload: true }),
  ApiError,
};

export default apiClient;
