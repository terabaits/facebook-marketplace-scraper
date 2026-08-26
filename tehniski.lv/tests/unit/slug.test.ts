import { describe, it, expect } from 'vitest';
import { slugify, diacriticFold } from '@/lib/slug';

describe('diacriticFold', () => {
  it('strips Latvian diacritics', () => {
    expect(diacriticFold('Rīgas')).toBe('Rigas');
    expect(diacriticFold('čau šo žēl')).toBe('cau so zel');
  });
  it('leaves ASCII unchanged', () => {
    expect(diacriticFold('hello')).toBe('hello');
  });
});

describe('slugify', () => {
  it('keeps Latvian diacritics', () => {
    expect(slugify('Rīgas satiksme')).toBe('rīgas-satiksme');
  });
  it('replaces spaces with dashes', () => {
    expect(slugify('Hello World')).toBe('hello-world');
  });
  it('strips punctuation', () => {
    expect(slugify('Hello, World!')).toBe('hello-world');
  });
  it('truncates to 80 chars', () => {
    const long = 'a'.repeat(100);
    expect(slugify(long).length).toBeLessThanOrEqual(80);
  });
  it('handles empty string', () => {
    expect(slugify('')).toBe('');
  });
});
