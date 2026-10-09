/**
 * Minimal markdown renderer for the notes preview pane.
 *
 * Security note: the input is HTML-escaped BEFORE any markup is applied, and
 * links are restricted to http(s), so `dangerouslySetInnerHTML` on the output
 * cannot inject scripts or `javascript:` URLs.
 */

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function renderInline(s: string): string {
  // `s` is already escaped at this point.
  // Protect code spans from emphasis/link processing via placeholders.
  const codes: string[] = [];
  let out = s.replace(/`([^`\n]+)`/g, (_m, c: string) => {
    codes.push(`<code>${c}</code>`);
    return `\uE000${codes.length - 1}\uE001`;
  });
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/(^|[^*\w])\*([^*\n]+)\*/g, '$1<em>$2</em>');
  out = out.replace(
    /\[([^\]]+)\]\((https?:[^)\s]+)\)/g,
    '<a href="$2" target="_blank" rel="noreferrer">$1</a>',
  );
  return out.replace(/\uE000(\d+)\uE001/g, (_m, i: string) => codes[Number(i)]);
}

export function renderMarkdown(src: string): string {
  const lines = escapeHtml(src).split('\n');
  const html: string[] = [];
  let inCode = false;
  let listOpen = false;

  const closeList = (): void => {
    if (listOpen) {
      html.push('</ul>');
      listOpen = false;
    }
  };

  for (const line of lines) {
    if (line.trim().startsWith('```')) {
      inCode = !inCode;
      html.push(inCode ? '<pre><code>' : '</code></pre>');
      continue;
    }
    if (inCode) {
      html.push(line + '\n');
      continue;
    }
    const heading = /^(#{1,3})\s+(.*)$/.exec(line);
    if (heading) {
      closeList();
      const level = heading[1].length;
      html.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
      continue;
    }
    // `>` was escaped to `&gt;` above.
    const quote = /^&gt;\s?(.*)$/.exec(line);
    if (quote) {
      closeList();
      html.push(`<blockquote>${renderInline(quote[1])}</blockquote>`);
      continue;
    }
    const item = /^[-*]\s+(.*)$/.exec(line);
    if (item) {
      if (!listOpen) {
        html.push('<ul>');
        listOpen = true;
      }
      html.push(`<li>${renderInline(item[1])}</li>`);
      continue;
    }
    if (line.trim() === '') {
      closeList();
      continue;
    }
    closeList();
    html.push(`<p>${renderInline(line)}</p>`);
  }
  closeList();
  if (inCode) {
    // Unclosed fence: close it rather than leaking markup state.
    html.push('</code></pre>');
  }
  return html.join('\n');
}
