// Note: keep this file free of `@prisma/client` imports so the type
// literal does not depend on Prisma client generation order. Consumers
// that need the Prisma enum value can `import { RunStatus } from '@prisma/client'`
// and cast / compare against the string-literal type defined here.

type RunStatus = 'in_progress' | 'awaiting_editor' | 'awaiting_subject' | 'writing' | 'published' | 'failed';

// Allowed transitions for the HIL workflow
const transitions: Record<RunStatus, RunStatus[]> = {
  in_progress:    ['awaiting_editor', 'failed'],
  awaiting_editor: ['awaiting_subject', 'in_progress', 'failed'],  // can go back to re-pick
  awaiting_subject: ['writing', 'awaiting_editor', 'failed'],       // can re-pick stories before subject
  writing:        ['published', 'awaiting_subject', 'failed'],     // can re-pick subject
  published:      [],                                                // terminal
  failed:         ['in_progress']                                    // admin can retry
};

export function canTransition(from: RunStatus, to: RunStatus): boolean {
  return transitions[from]?.includes(to) ?? false;
}

export function nextStatusFor(currentStep: 'pick-stories' | 'pick-subject' | 'write', currentStatus: RunStatus): RunStatus {
  if (currentStatus === 'failed') return 'in_progress';
  if (currentStep === 'pick-stories') return 'awaiting_subject';
  if (currentStep === 'pick-subject') return 'writing';
  return 'published';
}

export function stepForStatus(status: RunStatus): 'pick-stories' | 'pick-subject' | 'write' | 'review' {
  if (status === 'awaiting_editor' || status === 'in_progress') return 'pick-stories';
  if (status === 'awaiting_subject') return 'pick-subject';
  if (status === 'writing') return 'write';
  return 'review';  // published, failed
}
