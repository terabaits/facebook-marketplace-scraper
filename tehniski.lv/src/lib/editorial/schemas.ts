import { z } from 'zod';

// pick-stories step (also returns intro + shortlist per spec §3)
// Mavis is told: the response is strict JSON matching this schema; no prose around it.
export const pickStoriesSchema = z.object({
  candidates: z.array(z.object({
    story_id: z.string().min(1),
    title: z.string().min(1),
    source: z.string().min(1),
    reasoning: z.string().min(1).max(500),
    rank: z.number().int().positive()
  })).min(1).max(10),
  intro: z.string().min(1).max(500).optional(),       // ~1 paragraph Latvian intro
  shortlist: z.array(z.string()).max(20).optional(),  // titles of runner-up stories
  iteration_notes: z.string().max(2000).optional()
});
export type PickStoriesResponse = z.infer<typeof pickStoriesSchema>;

// pick-subject step: main + 3-5 alternatives
export const pickSubjectSchema = z.object({
  main: z.string().min(1).max(200),
  alternatives: z.array(z.string().min(1).max(200)).min(3).max(5),
  iteration_notes: z.string().max(2000).optional()
});
export type PickSubjectResponse = z.infer<typeof pickSubjectSchema>;

// write step: one per approved story
export const writeSchema = z.object({
  title_lv: z.string().min(1).max(200),               // Latvian title
  excerpt_lv: z.string().min(1).max(500),             // Latvian excerpt
  body_md: z.string().min(100).max(50_000),           // Latvian markdown body
  iteration_notes: z.string().max(2000).optional()
});
export type WriteResponse = z.infer<typeof writeSchema>;

// step → schema map
export const stepSchemas = {
  'pick-stories': pickStoriesSchema,
  'pick-subject': pickSubjectSchema,
  'write': writeSchema
} as const;
export type StepName = keyof typeof stepSchemas;
