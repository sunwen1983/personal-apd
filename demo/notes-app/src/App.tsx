import { Editor } from './components/Editor';
import { Sidebar } from './components/Sidebar';
import { useNotes } from './hooks/useNotes';

export default function App() {
  const {
    visibleNotes,
    allTags,
    totalCount,
    selected,
    selectedId,
    setSelectedId,
    query,
    setQuery,
    activeTag,
    setActiveTag,
    createNote,
    updateNote,
    deleteNote,
  } = useNotes();

  return (
    <div className="app">
      <header className="app-header">
        <h1>Notes</h1>
        <span className="count">
          {totalCount} {totalCount === 1 ? 'note' : 'notes'}
        </span>
      </header>
      <div className="app-body">
        <Sidebar
          notes={visibleNotes}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onNew={createNote}
          onDelete={deleteNote}
          query={query}
          onQuery={setQuery}
          tags={allTags}
          activeTag={activeTag}
          onTag={setActiveTag}
        />
        <main className="main">
          {selected ? (
            <Editor note={selected} onChange={(patch) => updateNote(selected.id, patch)} />
          ) : (
            <div className="empty-state">
              <p>Select a note, or create a new one to get started.</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
