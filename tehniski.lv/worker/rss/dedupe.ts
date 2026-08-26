import { createHash } from 'node:crypto';

export function urlHash(url: string): string {
  const u = new URL(url);
  u.hostname = u.hostname.toLowerCase();
  // strip utm_*
  for (const k of [...u.searchParams.keys()]) if (k.toLowerCase().startsWith('utm_')) u.searchParams.delete(k);
  let s = u.toString();
  // Strip trailing slash for non-root paths so /foo/ and /foo collide.
  // Keep the trailing slash on the bare root to keep example.com/ distinct from example.com.
  if (s.endsWith('/') && u.pathname !== '/') s = s.slice(0, -1);
  return createHash('sha256').update(s).digest('hex');
}

export function contentHash(text: string): string {
  // Normalize whitespace before hashing
  const norm = text.replace(/\s+/g, ' ').trim();
  return createHash('sha256').update(norm).digest('hex');
}

export function partitionBySeen<T extends { urlHash: () => string }>(items: T[], seen: Set<string>) {
  const newItems: T[] = [];
  for (const item of items) {
    const h = item.urlHash();
    if (seen.has(h)) continue;
    newItems.push(item);
  }
  return { newItems, seen };
}
