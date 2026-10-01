import { useCallback, useEffect, useRef, useState } from 'react';
import { createTodo, fetchTodos } from '../api/todoApi';

export function useTodos() {
  const [todos, setTodos] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const activeRequest = useRef(null);

  // Each load aborts the previous request so a slow, stale response can't
  // overwrite a newer one; the effect cleanup aborts on unmount.
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

  // Errors are rethrown so the form can show them next to the input.
  const addTodo = useCallback(
    async (description) => {
      await createTodo(description);
      await loadTodos();
    },
    [loadTodos]
  );

  return { todos, isLoading, error, addTodo, reload: loadTodos };
}
