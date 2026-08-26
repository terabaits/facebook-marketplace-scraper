import type { AdCreative } from '@prisma/client';

/**
 * Pick one creative from the list using a weighted random draw.
 * Returns the full creative object (not just id/weight) so callers can
 * render image/embed content without an extra round-trip.
 */
export function pickCreative<T extends Pick<AdCreative, 'id' | 'weight'>>(creatives: T[]): T | null {
  if (creatives.length === 0) return null;
  const total = creatives.reduce((s, c) => s + Math.max(1, c.weight), 0);
  let r = Math.random() * total;
  for (const c of creatives) {
    r -= Math.max(1, c.weight);
    if (r <= 0) return c;
  }
  return creatives[creatives.length - 1];
}
