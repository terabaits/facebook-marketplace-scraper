import { describe, it, expect } from 'vitest';
import { urlHash, contentHash, partitionBySeen } from '~worker/rss/dedupe';

describe('urlHash', () => {
  it('is stable', () => {
    expect(urlHash('https://example.com/foo')).toBe(urlHash('https://example.com/foo'));
  });
  it('normalizes trailing slashes', () => {
    expect(urlHash('https://example.com/foo/')).toBe(urlHash('https://example.com/foo'));
  });
  it('strips utm_* params', () => {
    expect(urlHash('https://example.com/foo?utm_source=x')).toBe(urlHash('https://example.com/foo'));
  });
  it('lowercases host', () => {
    expect(urlHash('https://EXAMPLE.com/foo')).toBe(urlHash('https://example.com/foo'));
  });
});

describe('contentHash', () => {
  it('hashes body text', () => {
    const a = contentHash('hello world');
    const b = contentHash('hello world');
    expect(a).toBe(b);
  });
  it('differs on different content', () => {
    expect(contentHash('hello')).not.toBe(contentHash('world'));
  });
});

describe('partitionBySeen', () => {
  it('separates new from already-seen', () => {
    const existing = new Set(['hash1', 'hash3']);
    const items = [
      { url: 'a', urlHash: () => 'hash1' },
      { url: 'b', urlHash: () => 'hash2' },
      { url: 'c', urlHash: () => 'hash3' },
      { url: 'd', urlHash: () => 'hash4' }
    ];
    const { newItems, seen } = partitionBySeen(items as any, existing);
    expect(newItems.map((i: any) => i.url)).toEqual(['b', 'd']);
    expect(seen).toEqual(new Set(['hash1', 'hash3']));
  });
});
