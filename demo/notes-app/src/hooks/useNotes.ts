import { useEffect, useMemo, useState } from 'react';
import type { Note, NotePatch } from '../types';
import { newId } from '../lib/ids';
import { loadNotes, saveNotes } from '../lib/store';

export interface NotesApi {
  visibleNotes: Note[];
  allTags: string[];
  totalCount: number;
  selected: Note | null;
  selectedId: string | null;
  setSelectedId: (id: string) => void;
  query: string;
  setQuery: (q: string) => void;
  activeTag: string | null;
  setActiveTag: (t: string | null) => void;
  createNote: () => void;
  updateNote: (id: string, patch: NotePatch) => void;
  deleteNote: (id: string) => void;
}

export function useNotes(): NotesApi {
  const [notes, setNotes] = useState<Note[]>(loadNotes);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [activeTag, setActiveTag] = useState<string | null>(null);

  useEffect(() => {
    saveNotes(notes);
  }, [notes]);

  // Keep the selection pointing at an existing note; select the newest note
  // on first load so a returning user doesn't land on an empty pane.
  useEffect(() => {
    if (notes.length === 0) {
      if (selectedId !== null) setSelectedId(null);
    } else if (selectedId === null || !notes.some((n) => n.id === selectedId)) {
      setSelectedId(notes[0].id);
    }
  }, [notes, selectedId]);

  const allTags = useMemo(() => {
    const set = new Set<string>();
    for (const n of notes) for (const t of n.tags) set.add(t);
    return [...set].sort();
  }, [notes]);

  const visibleNotes = useMemo(() => {
    const q = query.trim().toLowerCase();
    return notes
      .filter((n) => activeTag === null || n.tags.includes(activeTag))
      .filter(
        (n) =>
          q === '' ||
          n.title.toLowerCase().includes(q) ||
          n.body.toLowerCase().includes(q) ||
          n.tags.some((t) => t.toLowerCase().includes(q)),
      )
      .sort((a, b) => b.updatedAt - a.updatedAt);
  }, [notes, query, activeTag]);

  const selected = notes.find((n) => n.id === selectedId) ?? null;

  function createNote(): void {
    const now = Date.now();
    const note: Note = {
      id: newId(),
      title: 'Untitled note',
      body: '',
      tags: [],
      createdAt: now,
      updatedAt: now,
    };
    setNotes((prev) => [note, ...prev]);
    setSelectedId(note.id);
    setQuery('');
    setActiveTag(null);
  }

  function updateNote(id: string, patch: NotePatch): void {
    setNotes((prev) =>
      prev.map((n) => (n.id === id ? { ...n, ...patch, updatedAt: Date.now() } : n)),
    );
  }

  function deleteNote(id: string): void {
    setNotes((prev) => prev.filter((n) => n.id !== id));
  }

  return {
    visibleNotes,
    allTags,
    totalCount: notes.length,
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
  };
}
