import { describe, it, expect } from 'vitest';
import { pickCreative } from '@/lib/ads';

describe('pickCreative', () => {
  it('returns null for empty list', () => {
    expect(pickCreative([])).toBeNull();
  });
  it('picks a creative', () => {
    const creatives = [{ id: 'a', weight: 1 } as any, { id: 'b', weight: 1 } as any];
    const picked = pickCreative(creatives);
    expect(['a','b']).toContain(picked?.id);
  });
  it('respects weights (all weight=1 → roughly equal)', () => {
    const creatives = [{ id: 'a', weight: 1 } as any, { id: 'b', weight: 1 } as any];
    const counts = { a: 0, b: 0 };
    for (let i = 0; i < 1000; i++) {
      const p = pickCreative(creatives);
      if (p) counts[p.id as 'a'|'b']++;
    }
    expect(Math.abs(counts.a - counts.b)).toBeLessThan(100);
  });
});
