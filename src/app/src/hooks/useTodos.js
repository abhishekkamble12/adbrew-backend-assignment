import { useCallback, useEffect, useRef, useState } from 'react';
import { createTodo, fetchTodos } from '../api/todoApi';

/**
 * Owns the TODO list state and keeps it in sync with the backend.
 *
 * Every load aborts the previous in-flight request, so a slow, stale response
 * can never overwrite a newer one, and nothing updates state after unmount.
 */
export function useTodos() {
  const [todos, setTodos] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const activeRequest = useRef(null);

  const loadTodos = useCallback(async () => {
    if (activeRequest.current) {
      activeRequest.current.abort();
    }
    const controller = new AbortController();
    activeRequest.current = controller;

    setIsLoading(true);
    try {
      const data = await fetchTodos({ signal: controller.signal });
      setTodos(data);
      setError(null);
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message);
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    loadTodos();
    return () => {
      if (activeRequest.current) {
        activeRequest.current.abort();
      }
    };
  }, [loadTodos]);

  // Throws on failure so the caller (the form) can show the error inline.
  // After a successful create, the list is re-fetched from the backend so it
  // always reflects what is actually stored in MongoDB.
  const addTodo = useCallback(
    async (description) => {
      await createTodo(description);
      await loadTodos();
    },
    [loadTodos]
  );

  return { todos, isLoading, error, addTodo, reload: loadTodos };
}
