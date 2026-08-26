import { describe, it, expect } from 'vitest';
import { canTransition, nextStatusFor, stepForStatus } from '@/lib/editorial/state-machine';

describe('canTransition', () => {
  it('allows in_progress → awaiting_editor', () => {
    expect(canTransition('in_progress', 'awaiting_editor')).toBe(true);
  });
  it('rejects published → anything', () => {
    expect(canTransition('published', 'in_progress')).toBe(false);
  });
  it('allows failed → in_progress (retry)', () => {
    expect(canTransition('failed', 'in_progress')).toBe(true);
  });
});

describe('nextStatusFor', () => {
  it('pick-stories → awaiting_subject', () => {
    expect(nextStatusFor('pick-stories', 'awaiting_editor')).toBe('awaiting_subject');
  });
  it('pick-subject → writing', () => {
    expect(nextStatusFor('pick-subject', 'awaiting_subject')).toBe('writing');
  });
  it('write → published', () => {
    expect(nextStatusFor('write', 'writing')).toBe('published');
  });
});

describe('stepForStatus', () => {
  it('maps awaiting_editor → pick-stories', () => {
    expect(stepForStatus('awaiting_editor')).toBe('pick-stories');
  });
  it('maps writing → write', () => {
    expect(stepForStatus('writing')).toBe('write');
  });
  it('maps published → review', () => {
    expect(stepForStatus('published')).toBe('review');
  });
});
