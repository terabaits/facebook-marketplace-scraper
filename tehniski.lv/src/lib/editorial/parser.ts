import { z } from 'zod';
import { stepSchemas, type StepName } from './schemas';

export type ParseResult<T> =
  | { ok: true; data: T; warnings: string[] }
  | { ok: false; error: string; partialData?: unknown };

/**
 * Tolerant JSON parser for pasted responses.
 * Mavis sometimes wraps JSON in ```json ... ``` fences; sometimes adds a leading "Here you go:".
 * This function strips common wrappers before parsing, then validates against the step's Zod schema.
 */
export function parseStepResponse<T = unknown>(step: StepName, raw: string): ParseResult<T> {
  // 1) Try to extract JSON from the response (strip markdown fences, leading prose)
  const jsonText = extractJson(raw);
  if (!jsonText) return { ok: false, error: 'No JSON object found in response' };

  // 2) Try to parse
  let parsed: unknown;
  try { parsed = JSON.parse(jsonText); }
  catch (e) { return { ok: false, error: `Invalid JSON: ${(e as Error).message}` }; }

  // 3) Validate against the step schema
  const schema = stepSchemas[step];
  const result = schema.safeParse(parsed);
  if (!result.success) {
    const issues = result.error.issues.map(i => `${i.path.join('.')}: ${i.message}`).join('; ');
    return { ok: false, error: `Schema validation failed: ${issues}`, partialData: parsed };
  }

  return { ok: true, data: result.data as T, warnings: [] };
}

function extractJson(raw: string): string | null {
  let s = raw.trim();

  // Strip ```json ... ``` or ``` ... ``` fences
  const fence = s.match(/```(?:json)?\s*([\s\S]+?)\s*```/);
  if (fence) s = fence[1].trim();

  // Find the first '{' and the matching last '}'
  const start = s.indexOf('{');
  const end = s.lastIndexOf('}');
  if (start === -1 || end === -1 || end <= start) return null;
  return s.slice(start, end + 1);
}
