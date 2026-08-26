import { describe, it, expect } from 'vitest';
import { formatDateLv, formatDateTimeLv, formatNumberLv, formatRelativeLv } from '@/lib/format';

describe('formatDateLv', () => {
  it('formats UTC date as Latvian dd.mm.yyyy.', () => {
    expect(formatDateLv(new Date('2026-08-25T12:00:00Z'))).toBe('25.08.2026.');
  });
});

describe('formatDateTimeLv', () => {
  it('includes time in HH:MM format', () => {
    // August in Latvia is EEST (UTC+3), so 14:35Z -> 17:35 Riga
    expect(formatDateTimeLv(new Date('2026-08-25T14:35:00Z'))).toBe('25.08.2026. 17:35');
  });
});

describe('formatNumberLv', () => {
  it('uses space thousands and comma decimal', () => {
    // Latvian typography uses non-breaking space (U+00A0) for thousands separator
    expect(formatNumberLv(1234.56)).toBe('1\u00a0234,56');
  });
});

describe('formatRelativeLv', () => {
  const now = new Date('2026-08-25T12:00:00Z');
  it('shows "šodien" for same day', () => {
    expect(formatRelativeLv(new Date('2026-08-25T08:00:00Z'), now)).toBe('šodien');
  });
  it('shows "vakar" for 1 day ago', () => {
    expect(formatRelativeLv(new Date('2026-08-24T12:00:00Z'), now)).toBe('vakar');
  });
  it('shows "pirms N stundām" for same day older', () => {
    expect(formatRelativeLv(new Date('2026-08-25T09:00:00Z'), now)).toBe('pirms 3 stundām');
  });
  it('falls back to date for older', () => {
    expect(formatRelativeLv(new Date('2026-08-20T12:00:00Z'), now)).toBe('20.08.2026.');
  });
});
