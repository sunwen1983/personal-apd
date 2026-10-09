import { useMemo } from 'react';
import { renderMarkdown } from '../lib/markdown';

export function Preview({ source }: { source: string }) {
  // renderMarkdown escapes HTML before applying markup, so this is safe.
  const html = useMemo(() => renderMarkdown(source), [source]);
  return <div className="preview" dangerouslySetInnerHTML={{ __html: html }} />;
}
