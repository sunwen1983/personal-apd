import { useEffect, useState } from 'react';
import type { Note, NotePatch } from '../types';
import { parseTags } from '../lib/tags';
import { Preview } from './Preview';

type Mode = 'edit' | 'preview';

interface EditorProps {
  note: Note;
  onChange: (patch: NotePatch) => void;
}

export function Editor({ note, onChange }: EditorProps) {
  const [mode, setMode] = useState<Mode>('edit');
  // Local text state so in-progress input (e.g. a trailing comma) isn't
  // reformatted while typing; committed to the note on every change.
  const [tagsText, setTagsText] = useState(note.tags.join(', '));

  // Resync when switching to a different note. Intentionally keyed on id only:
  // syncing on tags would clobber in-progress typing.
  useEffect(() => {
    setTagsText(note.tags.join(', '));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [note.id]);

  function handleTagsInput(value: string): void {
    setTagsText(value);
    onChange({ tags: parseTags(value) });
  }

  return (
    <section className="editor">
      <input
        className="title-input"
        value={note.title}
        onChange={(e) => onChange({ title: e.target.value })}
        placeholder="Note title"
        aria-label="Note title"
      />
      <input
        className="tags-input"
        value={tagsText}
        onChange={(e) => handleTagsInput(e.target.value)}
        placeholder="tags, comma separated"
        aria-label="Note tags"
      />
      <div className="mode-tabs" role="tablist" aria-label="Edit or preview">
        <button
          role="tab"
          aria-selected={mode === 'edit'}
          className={mode === 'edit' ? 'tab active' : 'tab'}
          onClick={() => setMode('edit')}
        >
          Edit
        </button>
        <button
          role="tab"
          aria-selected={mode === 'preview'}
          className={mode === 'preview' ? 'tab active' : 'tab'}
          onClick={() => setMode('preview')}
        >
          Preview
        </button>
      </div>
      {mode === 'edit' ? (
        <textarea
          className="body-input"
          value={note.body}
          onChange={(e) => onChange({ body: e.target.value })}
          placeholder="Write markdown here…"
          aria-label="Note body (markdown)"
        />
      ) : (
        <div className="preview-wrap">
          <Preview source={note.body} />
        </div>
      )}
    </section>
  );
}
