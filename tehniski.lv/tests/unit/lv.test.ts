import { describe, it, expect } from 'vitest';
import { lv } from '@/lib/lv';

describe('lv.plural.comments', () => {
  it('handles 1', () => expect(lv.plural.comments(1)).toBe('1 komentārs'));
  it('handles 2-9 except 11', () => expect(lv.plural.comments(5)).toBe('5 komentāri'));
  it('handles 0', () => expect(lv.plural.comments(0)).toBe('0 komentāri'));
  it('handles 11 (exception)', () => expect(lv.plural.comments(11)).toBe('11 komentāri'));
  it('handles 21 (exception)', () => expect(lv.plural.comments(21)).toBe('21 komentārs'));
  it('handles 22', () => expect(lv.plural.comments(22)).toBe('22 komentāri'));
});
