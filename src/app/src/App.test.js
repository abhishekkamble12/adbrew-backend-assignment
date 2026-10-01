import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';

function jsonResponse(body, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  });
}

beforeEach(() => {
  global.fetch = jest.fn();
});

afterEach(() => {
  delete global.fetch;
});

test('renders TODOs fetched from the backend', async () => {
  fetch.mockReturnValueOnce(
    jsonResponse([
      { id: '1', description: 'Learn Docker' },
      { id: '2', description: 'Learn React' },
    ])
  );

  render(<App />);

  expect(await screen.findByText('Learn Docker')).toBeInTheDocument();
  expect(screen.getByText('Learn React')).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledWith('http://localhost:8000/todos', expect.any(Object));
});

test('shows an empty state when there are no TODOs', async () => {
  fetch.mockReturnValueOnce(jsonResponse([]));

  render(<App />);

  expect(await screen.findByText(/no todos yet/i)).toBeInTheDocument();
});

test('creates a TODO and refreshes the list from the backend', async () => {
  fetch
    .mockReturnValueOnce(jsonResponse([]))
    .mockReturnValueOnce(jsonResponse({ id: '1', description: 'Write tests' }, 201))
    .mockReturnValueOnce(jsonResponse([{ id: '1', description: 'Write tests' }]));

  render(<App />);
  await screen.findByText(/no todos yet/i);

  userEvent.type(screen.getByLabelText(/todo/i), '  Write tests  ');
  userEvent.click(screen.getByRole('button', { name: /add todo/i }));

  expect(await screen.findByText('Write tests')).toBeInTheDocument();

  const [url, options] = fetch.mock.calls[1];
  expect(url).toBe('http://localhost:8000/todos');
  expect(options.method).toBe('POST');
  expect(JSON.parse(options.body)).toEqual({ description: 'Write tests' });
  expect(fetch).toHaveBeenCalledTimes(3);
  expect(screen.getByLabelText(/todo/i)).toHaveValue('');
});

test('shows a validation error from the backend and keeps the input', async () => {
  fetch
    .mockReturnValueOnce(jsonResponse([]))
    .mockReturnValueOnce(
      jsonResponse(
        {
          error: 'This field may not be blank.',
          details: { description: ['This field may not be blank.'] },
        },
        400
      )
    );

  render(<App />);
  await screen.findByText(/no todos yet/i);

  userEvent.type(screen.getByLabelText(/todo/i), 'Bad todo');
  userEvent.click(screen.getByRole('button', { name: /add todo/i }));

  expect(await screen.findByRole('alert')).toHaveTextContent('This field may not be blank.');
  expect(screen.getByLabelText(/todo/i)).toHaveValue('Bad todo');
});

test('shows an error with retry when the list cannot be loaded', async () => {
  fetch
    .mockReturnValueOnce(jsonResponse({ error: 'The database is currently unavailable.', details: {} }, 503))
    .mockReturnValueOnce(jsonResponse([{ id: '1', description: 'Recovered' }]));

  render(<App />);

  expect(await screen.findByRole('alert')).toHaveTextContent('The database is currently unavailable.');

  userEvent.click(screen.getByRole('button', { name: /retry/i }));

  expect(await screen.findByText('Recovered')).toBeInTheDocument();
});

test('falls back to a generic message when the error body is not JSON', async () => {
  fetch.mockReturnValueOnce(
    Promise.resolve({ ok: false, status: 502, json: () => Promise.reject(new SyntaxError('not json')) })
  );

  render(<App />);

  expect(await screen.findByRole('alert')).toHaveTextContent('Request failed with status 502.');
});

test('shows a network error when the server is unreachable', async () => {
  fetch.mockReturnValueOnce(Promise.reject(new TypeError('Failed to fetch')));

  render(<App />);

  expect(await screen.findByRole('alert')).toHaveTextContent('Unable to reach the server.');
});

test('disables submit for blank input', async () => {
  fetch.mockReturnValueOnce(jsonResponse([]));

  render(<App />);
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));

  userEvent.type(screen.getByLabelText(/todo/i), '   ');

  expect(screen.getByRole('button', { name: /add todo/i })).toBeDisabled();
});
