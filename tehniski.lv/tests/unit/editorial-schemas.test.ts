import { describe, it, expect } from 'vitest';
import { pickStoriesSchema, pickSubjectSchema, writeSchema } from '@/lib/editorial/schemas';

describe('pickStoriesSchema', () => {
  it('accepts a minimal valid response', () => {
    const r = pickStoriesSchema.safeParse({
      candidates: [{ story_id: 'a', title: 't', source: 's', reasoning: 'r', rank: 1 }]
    });
    expect(r.success).toBe(true);
  });
  it('rejects empty candidates', () => {
    const r = pickStoriesSchema.safeParse({ candidates: [] });
    expect(r.success).toBe(false);
  });
  it('accepts intro and shortlist as optional', () => {
    const r = pickStoriesSchema.safeParse({
      candidates: [{ story_id: 'a', title: 't', source: 's', reasoning: 'r', rank: 1 }],
      intro: 'hello',
      shortlist: ['x', 'y']
    });
    expect(r.success).toBe(true);
  });
});

describe('pickSubjectSchema', () => {
  it('requires 3-5 alternatives', () => {
    expect(pickSubjectSchema.safeParse({ main: 'm', alternatives: ['a', 'b'] }).success).toBe(false);
    expect(pickSubjectSchema.safeParse({ main: 'm', alternatives: ['a', 'b', 'c'] }).success).toBe(true);
    expect(pickSubjectSchema.safeParse({ main: 'm', alternatives: ['a', 'b', 'c', 'd', 'e', 'f'] }).success).toBe(false);
  });
});

describe('writeSchema', () => {
  it('requires min 100 chars body_md', () => {
    expect(writeSchema.safeParse({ title_lv: 't', excerpt_lv: 'e', body_md: 'short' }).success).toBe(false);
    expect(writeSchema.safeParse({ title_lv: 't', excerpt_lv: 'e', body_md: 'x'.repeat(200) }).success).toBe(true);
  });
});
