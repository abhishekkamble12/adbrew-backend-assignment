import { useState } from 'react';

const MAX_DESCRIPTION_LENGTH = 500;

export function TodoForm({ onSubmit }) {
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const trimmedDescription = description.trim();

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!trimmedDescription || isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmit(trimmedDescription);
      setDescription('');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label htmlFor="todo">ToDo: </label>
        <input
          id="todo"
          type="text"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          maxLength={MAX_DESCRIPTION_LENGTH}
          disabled={isSubmitting}
        />
      </div>
      <div style={{ marginTop: '5px' }}>
        <button type="submit" disabled={!trimmedDescription || isSubmitting}>
          {isSubmitting ? 'Adding...' : 'Add ToDo!'}
        </button>
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
    </form>
  );
}
