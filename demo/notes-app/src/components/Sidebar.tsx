import type { Note } from '../types';

interface SidebarProps {
  notes: Note[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  query: string;
  onQuery: (q: string) => void;
  tags: string[];
  activeTag: string | null;
  onTag: (t: string | null) => void;
}

function formatDate(ts: number): string {
  return new Date(ts).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function Sidebar(props: SidebarProps) {
  const {
    notes,
    selectedId,
    onSelect,
    onNew,
    onDelete,
    query,
    onQuery,
    tags,
    activeTag,
    onTag,
  } = props;

  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <button className="btn primary" onClick={onNew}>
          + New note
        </button>
        <input
          className="search"
          type="search"
          placeholder="Search notes…"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          aria-label="Search notes"
        />
      </div>

      {tags.length > 0 && (
        <div className="tag-row" aria-label="Filter by tag">
          <button
            className={activeTag === null ? 'tag active' : 'tag'}
            onClick={() => onTag(null)}
          >
            all
          </button>
          {tags.map((t) => (
            <button
              key={t}
              className={activeTag === t ? 'tag active' : 'tag'}
              onClick={() => onTag(activeTag === t ? null : t)}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      <ul className="note-list">
        {notes.map((n) => (
          <li
            key={n.id}
            className={n.id === selectedId ? 'note-item selected' : 'note-item'}
          >
            <button className="note-select" onClick={() => onSelect(n.id)}>
              <span className="note-title">{n.title || 'Untitled note'}</span>
              <span className="note-meta">{formatDate(n.updatedAt)}</span>
              {n.tags.length > 0 && (
                <span className="note-tags">{n.tags.join(', ')}</span>
              )}
            </button>
            <button
              className="note-delete"
              title="Delete note"
              aria-label={`Delete ${n.title || 'untitled note'}`}
              onClick={() => {
                if (window.confirm('Delete this note?')) onDelete(n.id);
              }}
            >
              ×
            </button>
          </li>
        ))}
        {notes.length === 0 && (
          <li className="empty">No notes match. Create one to get started.</li>
        )}
      </ul>
    </aside>
  );
}
