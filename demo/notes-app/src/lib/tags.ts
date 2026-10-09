/** Parse a comma-separated tag string into a deduped, normalized list. */
export function parseTags(input: string): string[] {
  const seen = new Set<string>();
  for (const raw of input.split(',')) {
    const t = raw.trim().toLowerCase();
    if (t && !seen.has(t)) seen.add(t);
  }
  return [...seen];
}
