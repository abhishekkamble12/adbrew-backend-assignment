const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(message, status, details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

function extractErrorMessage(body, status) {
  if (body && typeof body.error === 'string') {
    return body.error;
  }
  if (body && typeof body === 'object') {
    // DRF validation errors look like {"field": ["message", ...]}
    const firstFieldErrors = Object.values(body).find(Array.isArray);
    if (firstFieldErrors && firstFieldErrors.length > 0) {
      return String(firstFieldErrors[0]);
    }
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
    throw new ApiError(extractErrorMessage(body, response.status), response.status, body);
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
