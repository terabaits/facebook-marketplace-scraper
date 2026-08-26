import type { StepName } from './schemas';

/**
 * v1 stub. In v2, this calls the LLM API with the packet and returns the response JSON.
 * For now, the UI gets a "manual paste required" marker and the admin pastes Mavis's response.
 */
export type RunStepResult =
  | { mode: 'paste_required'; step: StepName; reason: string }
  | { mode: 'completed'; data: unknown };

export async function runStep(step: StepName, packet: string): Promise<RunStepResult> {
  // v1: always returns a paste-required marker. v2: replace with API call.
  return {
    mode: 'paste_required',
    step,
    reason: 'LLM API not yet integrated. Copy the task packet into Mavis chat, paste the JSON response into the UI.'
  };
}
