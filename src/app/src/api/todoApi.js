const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// The API always returns {"error": ..., "details": ...}; the fallback is for
// responses that never reached Django, e.g. a proxy error page.
function extractErrorMessage(body, status) {
  if (body && typeof body.error === 'string') {
    return body.error;
  }
  return `Request failed with status ${status}.`;
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  } catch (error) {
    if (error.name === 'AbortError') {
      throw error;
    }
    throw new ApiError('Unable to reach the server. Please try again.', 0);
  }

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiError(extractErrorMessage(body, response.status), response.status);
  }
  return body;
}

export function fetchTodos({ signal } = {}) {
  return request('/todos', { signal });
}

export function createTodo(description) {
  return request('/todos', {
    method: 'POST',
    body: JSON.stringify({ description }),
  });
}
