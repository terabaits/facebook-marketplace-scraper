import { describe, it, expect } from 'vitest';
import { parseStepResponse } from '@/lib/editorial/parser';

describe('parseStepResponse — pick-stories', () => {
  it('parses bare JSON', () => {
    const r = parseStepResponse('pick-stories', JSON.stringify({
      candidates: [{ story_id: 'a', title: 't', source: 's', reasoning: 'r', rank: 1 }]
    }));
    expect(r.ok).toBe(true);
  });
  it('strips ```json fences', () => {
    const text = '```json\n' + JSON.stringify({ candidates: [{ story_id: 'a', title: 't', source: 's', reasoning: 'r', rank: 1 }] }) + '\n```';
    const r = parseStepResponse('pick-stories', text);
    expect(r.ok).toBe(true);
  });
  it('strips leading prose', () => {
    const text = 'Here you go:\n' + JSON.stringify({ candidates: [{ story_id: 'a', title: 't', source: 's', reasoning: 'r', rank: 1 }] });
    const r = parseStepResponse('pick-stories', text);
    expect(r.ok).toBe(true);
  });
  it('rejects invalid JSON', () => {
    const r = parseStepResponse('pick-stories', 'not json at all');
    expect(r.ok).toBe(false);
  });
  it('rejects schema-invalid response', () => {
    const r = parseStepResponse('pick-stories', JSON.stringify({ candidates: [] }));
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.partialData).toBeDefined();
  });
});
