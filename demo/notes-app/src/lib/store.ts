import type { Note } from '../types';

const STORAGE_KEY = 'personal-apd.notes.v1';

function isNote(v: unknown): v is Note {
  if (typeof v !== 'object' || v === null) return false;
  const o = v as Record<string, unknown>;
  return (
    typeof o.id === 'string' &&
    typeof o.title === 'string' &&
    typeof o.body === 'string' &&
    Array.isArray(o.tags) &&
    o.tags.every((t) => typeof t === 'string') &&
    typeof o.createdAt === 'number' &&
    typeof o.updatedAt === 'number'
  );
}

/** Load notes from localStorage; corrupt or missing data yields []. */
export function loadNotes(): Note[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isNote);
  } catch {
    return [];
  }
}

/** Persist notes; silently keeps them in memory if storage is unavailable. */
export function saveNotes(notes: Note[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(notes));
  } catch {
    // Quota exceeded or storage blocked (e.g. private mode) — the in-memory
    // state in the hook remains the source of truth for this session.
  }
}
