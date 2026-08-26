import { describe, it, expect, beforeEach } from 'vitest';
import { TokenBucket } from '@/lib/rate-limit';

describe('TokenBucket', () => {
  it('allows up to capacity requests', () => {
    const b = new TokenBucket(5, 60_000);
    for (let i = 0; i < 5; i++) expect(b.tryConsume('a')).toBe(true);
    expect(b.tryConsume('a')).toBe(false);
  });
  it('isolates buckets per key', () => {
    const b = new TokenBucket(1, 60_000);
    expect(b.tryConsume('a')).toBe(true);
    expect(b.tryConsume('b')).toBe(true);
  });
});
