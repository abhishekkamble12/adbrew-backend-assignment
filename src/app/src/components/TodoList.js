export function TodoList({ todos, isLoading, error, onRetry }) {
  if (error) {
    return (
      <div role="alert" className="error">
        <p>Could not load TODOs: {error}</p>
        <button type="button" onClick={onRetry}>
          Retry
        </button>
      </div>
    );
  }

  if (isLoading && todos.length === 0) {
    return <p>Loading TODOs...</p>;
  }

  if (todos.length === 0) {
    return <p>No TODOs yet. Add one below!</p>;
  }

  return (
    <ul>
      {todos.map((todo) => (
        <li key={todo.id}>{todo.description}</li>
      ))}
    </ul>
  );
}
